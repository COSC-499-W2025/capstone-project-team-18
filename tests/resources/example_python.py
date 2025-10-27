""" This file is the de facto script to run for the client. """

import os
import tkinter as tk
from tkinter import Menu, messagebox, PhotoImage

from Classes.Frames.switchable_frame import SwitchableFrame

from Classes.Util.server_req import ServerRequest
from Classes.Util.global_state import GlobalState
from .Util.file_domain import FileDomain


class App(tk.Tk):
    """
    This App class defines the top level visuals for the UI.
    This inculdes the header and the menu options.

    The App SHOULD NOT handle the logic of switching screens.
    That logic is handled in the App's display_frame and in the
    class SwitchableFrame.
    """

    # Main app screen
    display_frame: SwitchableFrame = None

    # Server Request
    server_req: ServerRequest = None
    global_state: GlobalState = None

    # Current logged in user role
    role: str = None
    user_login_id: str = None

    def __init__(self):
        """
        This is the very first script ran for the client!
        We start off in the in the Login Screen.

        We define the ServerRequest object that all other
        frames will use.
        """
        super().__init__()

        self.global_state = GlobalState()
        self.server_req = ServerRequest()

        self.create_app_wide_visuals()

        self.display_frame = SwitchableFrame(self)
        self.display_frame.pack()

    def create_app_wide_visuals(self):
        """
        This is the visuals APP wide
        """

        self.config(background='#230a3c')

        self.__place_menu()
        self.create_header()

    def create_header(self):
        """
        The header has a logo and a white bar. It should
        appear on the top of each and every frame
        """

        hdr = tk.Frame(self, background='white', relief="raised")
        # Stick to the top and expand to fill the x-axis
        hdr.pack(side=tk.TOP, fill=tk.X)

        imgcanvas = tk.Canvas(hdr, background='white',
                              height=60, width=46, highlightthickness=0)
        imgcanvas.pack(side=tk.LEFT, pady=(5, 4), padx=(5, 5))

        # Get the directory of the current file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the absolute path
        logo_path = os.path.join(base_dir, "img", "logo_small.png")

        logo = PhotoImage(file=logo_path)
        limg = tk.Label(imgcanvas, image=logo)
        limg.image = logo
        imgcanvas.create_image(23, 30, image=logo)

        text_frame = tk.Frame(hdr, background='white')
        text_frame.pack(side=tk.LEFT, pady=(10, 20))

        tk.Label(text_frame, text='T H E   U N I V E R S I T Y', fg='#230a3c', justify=tk.LEFT, bg='white',
                 font=('Veranda', 8, 'bold')).pack(anchor='w', pady=(0, 5))
        tk.Label(text_frame, text='O F   L A A S Q', fg='#230a3c', justify=tk.LEFT, bg='white',
                 font=('Veranda', 8, 'bold')).pack(anchor='w')

    def __place_menu(self):
        """
        Here we define the menu bar that will sit at the very
        top of the OS when ran locally and in at the top of the
        window when run in Docker
        """

        # create a menubar
        menubar = Menu(self)
        self.config(menu=menubar)

        # create a menu
        nav_menu = Menu(menubar)

        # add a menu item to the menu
        menu_commands = [
            {"label": "Exit", "command": self.destroy},
            {"label": "Go Back to Previous Screen",
                "command": lambda: self.display_frame.go_back()},
            {"label": "Log Out", "command": lambda: self.display_frame.log_out()},
            {"label": "View my Profile",
                "command": lambda: self.display_frame.show_my_profile()},
            {"label": "Big Cursor (Windows only)", "command": self.big_cursor}
        ]

        for command in menu_commands:
            nav_menu.add_command(
                label=command['label'], command=command['command'])

        # add the File menu to the menubar
        menubar.add_cascade(
            label="Navigation",
            menu=nav_menu
        )

    def big_cursor(self):
        self.config(cursor='@cursors/aero_arrow_xl.cur')

    def edit_app_aspects(self, title: str, geometry: str, resizable=False):
        self.title(title)
        self.geometry(geometry)
        self.resizable(resizable, resizable)

    def destroy(self):
        self.global_state.logout()
        super().destroy()


if __name__ == "__main__":

    app = App()
    app.mainloop()
