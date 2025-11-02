
import cmd
import re
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
            "(4) Configure Email for Git Stats\n"
            "Type 'back' or 'cancel' to return to this main menu\n"
            "Type help or ? to list commands\n"
        )
        self.prompt = '(PAF) '
        self.ruler = '-'  # overwrite default separator line ('=')
        self.cmd_history = []  # will store the user's previous 3 commands

        # Update with user input
        self.project_filepath = ''  # Will be overwritten with user input
        self.user_consent = False  # Milestone #1- Requirement #1, #4
        self.user_email = ''  # will be user's Git-associated email

        title = 'Project Artifact Miner'
        print(f'\n{title}')
        print(self.ruler * len(self.options.splitlines()[0]))
        print(self.options)

    def do_perms(self, arg):
        '''
        Provides consent statement. User may enter Y/N to agree or disagree.
        '''
        self.update_history(self.cmd_history, "perms")
        # TODO: agreement doesn't print properly if the terminal isn't wide enough
        agreement = (
            "Do you consent to this program accessing all files and/or folders"
            "\nin the filepath you provide and (if applicable) permission to use"
            "\nthe files and/or folders in 3rd party software?\n"
            "(Y/N) or type 'back'/'cancel' to return to main menu: "
        )
        while True:
            answer = input(agreement).strip()

            # Check for cancel first
            # user entered 'back'/'cancel'
            if self._handle_cancel_input(answer):
                print("\n" + self.options)
                break

            answer = answer.upper()
            if answer == 'Y':  # user consents
                self.user_consent = True
                print("\nThank you for consenting. You may now continue.")
                print("\n" + self.options)
                break
            elif answer == 'N':  # user doesn't consent
                print("Consent not given. Exiting application...")
                return True  # tells cmdloop() to exit
            else:  # invalid input from user
                # Make sure this matches your actual error message
                print("Invalid response. Please enter 'Y', 'N', 'back', or 'cancel'.")

    def do_filepath(self, arg):
        '''User specifies the project's filepath'''
        self.update_history(self.cmd_history, "filepath")

        prompt = "Paste or type the full filepath to your project folder: (or 'back' / 'cancel' to return): "
        answer = input(prompt).strip()

        # Check if user wants to cancel
        if self._handle_cancel_input(answer):
            print("\n" + self.options)
            return  # Return to main menu

        # Process the filepath
        self.project_filepath = answer
        print("\nFilepath successfully received")
        print(self.project_filepath)
        print("\n" + self.options)

    def do_begin(self, arg):
        '''Begin the mining process. User must give consent and provide filepath prior.'''
        self.update_history(self.cmd_history, "begin")

        if self.user_consent:
            start_miner(self.project_filepath)
        else:
            print(
                "\nError: Missing consent. Type perms or 1 to read user permission agreement.")
            print("\n" + self.options)

    def update_history(self, cmd_history: list, cmd: str):
        '''
        We will track the user's history (entered commands) so that they can go back if they wish.
        This function updated the `cmd_history` list to do so.
        '''
        if len(cmd_history) == 3:  # only track their 3 most recent commands
            cmd_history.pop(0)  # remove the oldest item (first item)
        cmd_history.append(cmd)  # add new command to the end

        return cmd_history

    def do_back(self, arg):
        '''Return to the previous screen'''

        if len(self.cmd_history) > 1:  # Need at least 2 items to go back
            # Get the last command (the one we want to go back to)
            previous_cmd = self.cmd_history[-1]  # Get last command
            self.cmd_history.pop()  # Remove current command from history

            match previous_cmd:
                case "perms":
                    return self.do_perms(arg)
                case "filepath":
                    return self.do_filepath(arg)
                case "begin":
                    return self.do_begin(arg)
        else:
            print("\nNo previous command to return to.")
            print(self.options)

    def _handle_cancel_input(self, user_input):
        '''
        Helper method to check if user wants to cancel and handle it.
        Returns True if cancel was triggered, False otherwise.
        '''
        if user_input.strip().lower() in ['back', 'cancel']:
            # Remove the current command from history since user is cancelling
            if len(self.cmd_history) > 0:
                cancelled_cmd = self.cmd_history.pop()  # Now correctly removes from end
                print(f"\nCancelled '{cancelled_cmd}' operation.")
            else:
                print("\nReturning to main menu.")
            return True

        return False

    def do_email(self, arg):
        '''
        Add an email to the user's configuration such that inidividual contributions can be measured in a Git-tracked project
        '''
        self.update_history(self.cmd_history, "email")

        prompt = "Enter the email you use for your Git/GitHub account: (or 'back' / 'cancel' to return): "
        answer = input(prompt).strip()

        # Check if user wants to cancel
        if self._handle_cancel_input(answer):
            print("\n" + self.options)
            return  # Return to main menu

        while (not self.is_valid_email(answer)):
            prompt = "Please enter a valid email: (or 'back' / 'cancel' to return): "
            answer = input(prompt).strip()

            # Check if user wants to cancel
            if self._handle_cancel_input(answer):
                print("\n" + self.options)
                return  # Return to main menu

        # Process the filepath
        self.user_email = answer
        print("\nEmail successfully received")
        print(self.user_email)
        print("\n" + self.options)

    def is_valid_email(self, email: str) -> bool:
        """Email validation helper method."""
        EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(EMAIL_REGEX, email))

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
            "4": self.do_email,
        }

        # Make commands case-insensitive
        func = commands.get(line.strip().lower())
        if func:
            return func("")
        else:
            print(f"Unknown command: {line}. Type 'help' or '?' for options.")

    def do_exit(self, arg):
        '''Exits the program.'''
        print('Exiting the program...')
        return True
