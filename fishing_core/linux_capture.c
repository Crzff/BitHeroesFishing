/* wlr-screencopy v1 + wl_shm; firmas del protocolo MIT de Simon Ser (2018)
 * y Andri Yngvason (2019). Licencia completa en THIRD_PARTY_NOTICES.md.
 * https://github.com/swaywm/wlr-protocols/blob/master/unstable/wlr-screencopy-unstable-v1.xml
 * ponytail: un monitor 1920x1080, escala 1; bindings generados si se amplia el perfil.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <poll.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>

static const struct wl_interface frame_interface;
static const struct wl_interface *region_types[] = {
    &frame_interface, NULL, &wl_output_interface, NULL, NULL, NULL, NULL
};
static const struct wl_message capture_requests[] = {
    {"capture_output", "nio", region_types},
    {"capture_output_region", "nioiiii", region_types}, {"destroy", "", NULL}
};
static const struct wl_interface capture_interface = {
    "zwlr_screencopy_manager_v1", 1, 3, capture_requests, 0, NULL
};
static const struct wl_interface *buffer_types[] = {&wl_buffer_interface};
static const struct wl_message frame_requests[] = {
    {"copy", "o", buffer_types}, {"destroy", "", NULL}
};
static const struct wl_message frame_events[] = {
    {"buffer", "uuuu", NULL}, {"flags", "u", NULL},
    {"ready", "uuu", NULL}, {"failed", "", NULL}
};
static const struct wl_interface frame_interface = {
    "zwlr_screencopy_frame_v1", 1, 2, frame_requests, 4, frame_events
};

struct capture {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_shm *shm;
    struct wl_output *output;
    struct wl_proxy *manager, *frame;
    struct wl_buffer *buffer;
    void *pixels;
    size_t size;
    uint32_t width, height, stride, flags;
    int outputs, complete, invalid;
};

static int64_t now_ms(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

/* No roundtrip/dispatch bloqueante: un compositor roto no impide F8/parada. */
static int wait_copy(struct capture *c) {
    int64_t deadline = now_ms() + 750;
    while (!c->complete && !c->invalid) {
        while (wl_display_prepare_read(c->display) != 0) {
            if (wl_display_dispatch_pending(c->display) < 0) return -1;
            if (c->complete || c->invalid) return c->invalid ? -1 : 0;
        }
        if (wl_display_flush(c->display) < 0) {
            wl_display_cancel_read(c->display);
            return -1;
        }
        int remaining = (int)(deadline - now_ms());
        struct pollfd fd = {wl_display_get_fd(c->display), POLLIN, 0};
        int result = remaining > 0 ? poll(&fd, 1, remaining) : 0;
        if (result <= 0 || !(fd.revents & POLLIN)) {
            wl_display_cancel_read(c->display);
            if (result == 0) errno = ETIMEDOUT;
            return -1;
        }
        if (wl_display_read_events(c->display) < 0 ||
            wl_display_dispatch_pending(c->display) < 0) return -1;
    }
    return c->invalid ? -1 : 0;
}

static void global_capture(void *data, struct wl_registry *registry, uint32_t name,
                           const char *interface, uint32_t version) {
    (void)version;
    struct capture *c = data;
    if (strcmp(interface, capture_interface.name) == 0)
        c->manager = wl_registry_bind(registry, name, &capture_interface, 1);
    else if (strcmp(interface, "wl_shm") == 0)
        c->shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
    else if (strcmp(interface, "wl_output") == 0) {
        if (++c->outputs == 1)
            c->output = wl_registry_bind(registry, name, &wl_output_interface, 1);
        else c->invalid = 1;
    }
}

static void removed_capture(void *data, struct wl_registry *registry, uint32_t name) {
    (void)registry; (void)name;
    ((struct capture *)data)->invalid = 1;
}

static void done_capture(void *data, struct wl_callback *callback, uint32_t serial) {
    (void)callback; (void)serial;
    ((struct capture *)data)->complete = 1;
}

static void copy_buffer(void *data, struct wl_proxy *frame, uint32_t format,
                        uint32_t width, uint32_t height, uint32_t stride) {
    struct capture *c = data;
    if (c->buffer || width != c->width || height != c->height ||
        stride < width * 4 || stride > 1920 * 4 + 256 ||
        (format != WL_SHM_FORMAT_XRGB8888 && format != WL_SHM_FORMAT_ARGB8888)) {
        c->invalid = 1;
        return;
    }
    c->stride = stride;
    c->size = (size_t)stride * height;
    int fd = memfd_create("bitheroes-frame", MFD_CLOEXEC);
    if (fd < 0) { c->invalid = 1; return; }
    if (ftruncate(fd, (off_t)c->size) < 0) {
        close(fd); c->invalid = 1; return;
    }
    c->pixels = mmap(NULL, c->size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (c->pixels == MAP_FAILED) {
        c->pixels = NULL; close(fd); c->invalid = 1; return;
    }
    struct wl_shm_pool *pool = wl_shm_create_pool(c->shm, fd, (int32_t)c->size);
    close(fd);
    if (!pool) { c->invalid = 1; return; }
    c->buffer = wl_shm_pool_create_buffer(pool, 0, (int32_t)width, (int32_t)height,
                                        (int32_t)stride, format);
    wl_shm_pool_destroy(pool);
    if (!c->buffer) { c->invalid = 1; return; }
    wl_proxy_marshal_flags(frame, 0, NULL, 1, 0, c->buffer);
}

static void copy_flags(void *data, struct wl_proxy *frame, uint32_t flags) {
    (void)frame;
    struct capture *c = data;
    c->flags = flags;
    if (flags & ~1u) c->invalid = 1;
}

static void copy_ready(void *data, struct wl_proxy *frame,
                       uint32_t hi, uint32_t lo, uint32_t ns) {
    (void)frame; (void)hi; (void)lo;
    struct capture *c = data;
    if (!c->buffer || ns >= 1000000000u) c->invalid = 1;
    c->complete = 1;
}

static void copy_failed(void *data, struct wl_proxy *frame) {
    (void)frame;
    ((struct capture *)data)->invalid = 1;
}

static const struct {
    void (*buffer)(void *, struct wl_proxy *, uint32_t, uint32_t, uint32_t, uint32_t);
    void (*flags)(void *, struct wl_proxy *, uint32_t);
    void (*ready)(void *, struct wl_proxy *, uint32_t, uint32_t, uint32_t);
    void (*failed)(void *, struct wl_proxy *);
} copy_listener = {copy_buffer, copy_flags, copy_ready, copy_failed};

static void clear_frame(struct capture *c) {
    if (c->frame) wl_proxy_marshal_flags(c->frame, 1, NULL, 1, WL_MARSHAL_FLAG_DESTROY);
    if (c->buffer) wl_buffer_destroy(c->buffer);
    if (c->pixels) munmap(c->pixels, c->size);
    c->frame = NULL; c->buffer = NULL; c->pixels = NULL;
}

void fishing_capture_close(struct capture *c) {
    if (!c) return;
    clear_frame(c);
    if (c->manager) wl_proxy_destroy(c->manager);
    if (c->output) wl_output_destroy(c->output);
    if (c->shm) wl_shm_destroy(c->shm);
    if (c->registry) wl_registry_destroy(c->registry);
    if (c->display) wl_display_disconnect(c->display);
    free(c);
}

struct capture *fishing_capture_open(void) {
    static const struct wl_registry_listener registry_listener = {global_capture, removed_capture};
    static const struct wl_callback_listener sync_listener = {done_capture};
    struct capture *c = calloc(1, sizeof(*c));
    if (!c) return NULL;
    c->display = wl_display_connect(NULL);
    if (!c->display) goto failed;
    c->registry = wl_display_get_registry(c->display);
    if (!c->registry) goto failed;
    wl_registry_add_listener(c->registry, &registry_listener, c);
    struct wl_callback *sync = wl_display_sync(c->display);
    if (!sync) goto failed;
    wl_callback_add_listener(sync, &sync_listener, c);
    int result = wait_copy(c);
    wl_callback_destroy(sync);
    if (result < 0 || !c->manager || !c->shm || !c->output || c->outputs != 1) goto failed;
    return c;
failed:
    fishing_capture_close(c);
    return NULL;
}

int fishing_capture_grab(struct capture *c, int x, int y, int width, int height,
                         unsigned char *dest, size_t capacity) {
    if (!c || c->invalid || !dest || x < 0 || y < 0 || width <= 0 || height <= 0 ||
        width > 1920 - x || height > 1080 - y || x > 1920 || y > 1080 ||
        capacity != (size_t)width * height * 4) return -1;
    c->complete = 0; c->flags = 0;
    c->width = (uint32_t)width; c->height = (uint32_t)height;
    c->frame = wl_proxy_marshal_flags(c->manager, 1, &frame_interface, 1, 0,
                                      NULL, 0, c->output, x, y, width, height);
    if (!c->frame) return -1;
    wl_proxy_add_listener(c->frame, (void (**)(void))&copy_listener, c);
    int result = wait_copy(c);
    if (result == 0) {
        for (int row = 0; row < height; row++) {
            int source_row = c->flags & 1u ? height - row - 1 : row;
            memcpy(dest + (size_t)row * width * 4,
                   (unsigned char *)c->pixels + (size_t)source_row * c->stride, (size_t)width * 4);
        }
    } else c->invalid = 1; /* Ningun frame viejo puede reutilizarse tras un fallo. */
    clear_frame(c);
    return result;
}
