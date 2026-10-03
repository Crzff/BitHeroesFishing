"""Paleta propia inspirada en las ventanas de Bit Heroes; sin recursos del juego."""

COLOR_BG = '#172b38'
COLOR_CARD = '#514538'
COLOR_ACCENT = '#705034'
COLOR_HOVER = '#775535'
COLOR_FRAME = '#b7afa3'
COLOR_SHADOW = '#171512'
COLOR_INSET = '#302a23'
COLOR_GOLD = '#f2d48a'
COLOR_SUCCESS = '#a8ec65'
COLOR_DANGER = '#ffada3'
COLOR_TEXT = '#fff8e5'
COLOR_TEXT_DIM = '#d9cdbb'

# Relieves y foco nativos de Tk: https://docs.python.org/3/library/tkinter.html
WINDOW_STYLE = dict(bg=COLOR_FRAME, bd=5, relief='ridge', highlightthickness=2,
                    highlightbackground=COLOR_SHADOW)
PANEL_STYLE = dict(bg=COLOR_CARD, bd=3, relief='sunken', highlightthickness=1,
                   highlightbackground=COLOR_FRAME)
TITLE_STYLE = dict(bg='#3b2e22', fg=COLOR_GOLD, font=('Courier', 18, 'bold'),
                   bd=3, relief='ridge', pady=6)
PRIMARY_STYLE = dict(fg=COLOR_TEXT, activeforeground=COLOR_TEXT,
                     font=('Courier', 13, 'bold'), bd=4, relief='raised', pady=5,
                     disabledforeground='#c7baa8', highlightthickness=2,
                     highlightbackground=COLOR_SHADOW, highlightcolor=COLOR_GOLD,
                     takefocus=True, cursor='hand2')
START_STYLE = dict(PRIMARY_STYLE, bg='#426b0e', activebackground='#4c7912')
STOP_STYLE = dict(PRIMARY_STYLE, bg='#a52828', activebackground='#b63030')

# Opciones públicas: https://customtkinter.tomschimansky.com/documentation/widgets/
BUTTON_STYLE = dict(fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER,
                    text_color=COLOR_TEXT, text_color_disabled=COLOR_TEXT_DIM,
                    border_width=2, border_color=COLOR_FRAME, corner_radius=0)
ENTRY_STYLE = dict(fg_color=COLOR_INSET, border_color=COLOR_FRAME, corner_radius=0,
                   text_color=COLOR_TEXT)
MENU_STYLE = dict(fg_color=COLOR_INSET, button_color=COLOR_ACCENT,
                  button_hover_color=COLOR_HOVER, corner_radius=0,
                  text_color=COLOR_TEXT, text_color_disabled=COLOR_TEXT_DIM,
                  dropdown_fg_color=COLOR_INSET, dropdown_hover_color=COLOR_ACCENT,
                  dropdown_text_color=COLOR_TEXT)
