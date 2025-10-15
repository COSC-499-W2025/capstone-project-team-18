"""
This file is the starting script for the application
"""
import cmd


class ArtifactMiner(cmd.Cmd):
    cmd_history = []  # will store the user's previous 3 commands
    # Config for CIL
    intro = (
        "\nChoose one of the following options:"
        "\n(1) Permissions"
        "\n(2) Set filepath"
        "\n(3) Begin Artifact Miner"
        "\nType help or ? to list commands\n"
    )
    prompt = '(PAF) '
    ruler = '-'  # overwrite default seaparator line ('=')

    # Get from user input
    project_filepath = ''  # Will be overwritten with user input
    user_consent = False  # Milestone #1, requirement #1, #4

    def update_history(self, cmd_history: list, cmd: str):
        if len(cmd_history) == 3:
            cmd_history.pop()  # remove the last item
        cmd_history.insert(0, cmd)
        return cmd_history

    def do_perms(self, arg):
        '''
        Provides consent statement. User may enter Y/N to agree or disagree.
        '''
        self.update_history(self.cmd_history, "perms")
        agreement = (
            "Do you consent to this program accessing all files and/or folders "
            "in the filepath you provide and (if applicable) permission to use "
            "the files and/or folders in 3rd party software? \n(Y/N): "
        )
        while True:
            answer = input(agreement).strip().upper()
            if answer == 'Y':
                self.user_consent = True
                print("\nThank you for consenting. You may now continue.")
                print(self.intro)
                break
            elif answer == 'N':
                print("Consent not given. Exiting application...")
                return True  # tells cmdloop() to exit
            else:
                print("Invalid response. Please enter 'Y' or 'N'.")

    def do_filepath(self, arg):
        '''User specifies the project's filepath'''
        self.update_history(self.cmd_history, "filepath")

        prompt = "Paste or type the full filepath to your project folder: "
        self.project_filepath = input(prompt).strip()
        print("\nFilepath successfully received")
        print(self.project_filepath)
        print(self.intro)

    def do_begin(self, arg):
        '''Begin the mining process. User must give consent and provide filepath prior.'''
        self.update_history(self.cmd_history, "begin")

        if self.user_consent:
            try:  # verify valid filepath
                with open(self.project_filepath) as project:
                    print('TODO: Implement')
            except FileNotFoundError:
                print("Error: Invalid file. Please try again.")
                self.do_filepath(arg)
        else:
            print(
                "\nError: Missing consent. Type perms or 1 to read user permission agreement.")
            print(self.intro)

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


if __name__ == '__main__':
    ArtifactMiner().cmdloop()
