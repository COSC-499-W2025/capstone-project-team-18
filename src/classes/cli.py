"""
This file defines the command-line interface (CLI)
for the Artifact Miner application using the cmd module.
"""

import cmd
from app import start_miner


class ArtifactMiner(cmd.Cmd):
    def __init__(self):
        super().__init__()

        # Config for CLI
        self.options = (
            "Choose one of the following options:\n"
            "(1) Permissions\n"
            "(2) Set filepath\n"
            "(3) Begin Artifact Miner\n"
            "Type help or ? to list commands\n"
        )
        self.prompt = '(PAF) '
        self.ruler = '-'  # overwrite default separator line ('=')
        self.cmd_history = []  # will store the user's previous 3 commands

        # Update with user input
        self.project_filepath = ''  # Will be overwritten with user input
        self.user_consent = False  # Milestone #1- Requirement #1, #4

        title = 'Project Artifact Miner'
        print(f'\n{title}')
        print(self.ruler * len(self.options.splitlines()[0]))
        print(self.options)

    def update_history(self, cmd_history: list, cmd: str):
        '''
        We will track the user's history (entered commands) so that they can go back if they wish.
        This function updated the `cmd_history` list to do so.
        '''
        if len(cmd_history) == 3:  # we'll only track their 3 most recent commands
            cmd_history.pop()  # remove the last item
        cmd_history.insert(0, cmd)  # add new command
        return cmd_history

    def do_perms(self, arg):
        '''
        Provides consent statement. User may enter Y/N to agree or disagree.
        '''
        self.update_history(self.cmd_history, "perms")
        # TODO: agreement doesn't print properly if the terminal isn't wide enough
        agreement = (
            "Do you consent to this program accessing all files and/or folders"
            "\nin the filepath you provide and (if applicable) permission to use"
            "\nthe files and/or folders in 3rd party software?\n(Y/N):"
        )
        while True:
            answer = input(agreement).strip().upper()
            if answer == 'Y':  # user consents
                self.user_consent = True
                print("\nThank you for consenting. You may now continue.")
                print(self.options)
                break
            elif answer == 'N':  # user doesn't consent
                print("Consent not given. Exiting application...")
                return True  # tells cmdloop() to exit
            else:  # invalid input from user
                print("Invalid response. Please enter 'Y' or 'N'.")

    def do_filepath(self, arg):
        '''User specifies the project's filepath'''
        self.update_history(self.cmd_history, "filepath")

        prompt = "Paste or type the full filepath to your project folder: "
        self.project_filepath = input(prompt).strip()
        print("\nFilepath successfully received")
        print(self.project_filepath)
        print(self.options)

    def do_begin(self, arg):
        '''Begin the mining process. User must give consent and provide filepath prior.'''
        self.update_history(self.cmd_history, "begin")

        if self.user_consent:
            start_miner(self.project_filepath)
        else:
            print(
                "\nError: Missing consent. Type perms or 1 to read user permission agreement.")
            print(self.options)

    def do_back(self, arg):
        '''Return to the previous screen'''
        print(str(self.cmd_history))
        if len(self.cmd_history) > 0:
            match self.cmd_history[-1]:
                case "perms":
                    self.cmd_history.pop()
                    return self.do_perms(arg)
                case "filepath":
                    self.cmd_history.pop()
                    return self.do_filepath(arg)
                case "begin":
                    self.cmd_history.pop()
                    return self.do_begin(arg)

    def default(self, line):
        '''
        Overwrite the `default()` function so that our program
        accepts, for example, either '1' or 'perms' as input to
        call the `do_perms()` function.
        '''
        commands = {
            "1": self.do_perms,
            "2": self.do_filepath,
            "3": self.do_begin,
        }
        func = commands.get(line.strip())
        if func:
            return func("")
        else:
            print(f"Unknown command: {line}. Type 'help' or '?' for options.")

    def do_exit(self, arg):
        '''Exits the program.'''
        print('Exiting the program...')
        return True
