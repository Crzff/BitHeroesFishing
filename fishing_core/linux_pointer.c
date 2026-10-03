/* Puntero virtual Wayland v1; no necesita /dev/uinput ni un daemon root.
 * Firmas verificadas en el protocolo MIT de Josef Gajdusek (2019):
 * https://github.com/swaywm/wlr-protocols/blob/master/unstable/wlr-virtual-pointer-unstable-v1.xml
 * ponytail: solo puntero v1 y 1920x1080; generar bindings si se amplian protocolos.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <wayland-client.h>

static const struct wl_interface pointer_interface;
static const struct wl_interface *create_types[] = {
    &wl_seat_interface, &pointer_interface
};
static const struct wl_message pointer_requests[] = {
    {"motion", "uff", NULL}, {"motion_absolute", "uuuuu", NULL},
    {"button", "uuu", NULL}, {"axis", "uuf", NULL}, {"frame", "", NULL},
    {"axis_source", "u", NULL}, {"axis_stop", "uu", NULL},
    {"axis_discrete", "uufi", NULL}, {"destroy", "", NULL}
};
static const struct wl_interface pointer_interface = {
    "zwlr_virtual_pointer_v1", 1, 9, pointer_requests, 0, NULL
};
static const struct wl_message manager_requests[] = {
    {"create_virtual_pointer", "?on", create_types}, {"destroy", "", NULL}
};
static const struct wl_interface manager_interface = {
    "zwlr_virtual_pointer_manager_v1", 1, 2, manager_requests, 0, NULL
};

struct pointer {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_proxy *manager;
    struct wl_proxy *device;
    int pressed;
};

static void global(void *data, struct wl_registry *registry, uint32_t name,
                   const char *interface, uint32_t version) {
    (void)version;
    struct pointer *p = data;
    if (strcmp(interface, manager_interface.name) == 0)
        p->manager = wl_registry_bind(registry, name, &manager_interface, 1);
}

static void removed(void *data, struct wl_registry *registry, uint32_t name) {
    (void)data; (void)registry; (void)name;
}

static const struct wl_registry_listener listener = {global, removed};

static uint32_t milliseconds(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (uint32_t)((uint64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000);
}

int fishing_pointer_button(struct pointer *p, int pressed) {
    if (!p || !p->device) return -1;
    wl_proxy_marshal_flags(p->device, 2, NULL, 1, 0,
                           milliseconds(), 0x110u, (uint32_t)!!pressed);
    wl_proxy_marshal_flags(p->device, 4, NULL, 1, 0);
    p->pressed = !!pressed;
    return wl_display_roundtrip(p->display);
}

void fishing_pointer_close(struct pointer *p) {
    if (!p) return;
    if (p->device) {
        if (p->pressed) fishing_pointer_button(p, 0);
        wl_proxy_marshal_flags(p->device, 8, NULL, 1, WL_MARSHAL_FLAG_DESTROY);
    }
    if (p->manager) wl_proxy_destroy(p->manager);
    if (p->registry) wl_registry_destroy(p->registry);
    if (p->display) wl_display_disconnect(p->display);
    free(p);
}

struct pointer *fishing_pointer_open(void) {
    struct pointer *p = calloc(1, sizeof(*p));
    if (!p) return NULL;
    p->display = wl_display_connect(NULL);
    if (!p->display) goto failed;
    p->registry = wl_display_get_registry(p->display);
    if (!p->registry) goto failed;
    wl_registry_add_listener(p->registry, &listener, p);
    if (wl_display_roundtrip(p->display) < 0 || !p->manager) goto failed;
    p->device = wl_proxy_marshal_flags(p->manager, 0, &pointer_interface, 1, 0,
                                      NULL, NULL);
    if (!p->device || wl_display_roundtrip(p->display) < 0) goto failed;
    return p;
failed:
    fishing_pointer_close(p);
    return NULL;
}

int fishing_pointer_move(struct pointer *p, uint32_t x, uint32_t y) {
    if (!p || !p->device || x >= 1920 || y >= 1080) return -1;
    wl_proxy_marshal_flags(p->device, 1, NULL, 1, 0,
                           milliseconds(), x, y, 1920u, 1080u);
    wl_proxy_marshal_flags(p->device, 4, NULL, 1, 0);
    return wl_display_roundtrip(p->display);
}
