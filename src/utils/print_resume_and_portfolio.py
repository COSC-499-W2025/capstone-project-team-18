'''
This file contains functions to format and print the
resume items and portfolio
'''
from typing import Optional
from src.classes.resume import Resume
from src.classes.report import ProjectReport, UserReport
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resume_CLI_stringify(user_report: UserReport, email: Optional[str]):
    '''
    Given a `UserReport` object, print generate the
    resume items of the report and print them to
    the CLI

    Example Output:
    ```
    ---------------------------Resume---------------------------
    COSC-304-Project : 2024-11-18 00:02:28 - 2024-12-07 07:14:31
       - Project was coded using the SQL language
       - Collaborated in a team of 1 contributors
       - Authored 61.54% of commits
       - Accounted for 1.88% of total contribution in the final deliverable

    selectify : 2023-06-15 20:52:37 - 2023-12-01 20:17:35
       - Implemented code mainly in HTML and also in Python, CSS
       - Utilized skills /static/styles.css, dotenv, base64
       - I individually designed, developed, and led the project
       - Accounted for 85.68% of total contribution in the final deliverable
    ------------------------------------------------------------
    ```
    '''
    resume = user_report.generate_resume(email)
    try:
        resume_header_len = len(
            f'{resume.items[0].title} : {resume.items[0].start_date} - {resume.items[0].end_date}')
        header_line = "Resume".center(resume_header_len, '-')

        print(header_line)
        print(f'{resume}{'-' * len(header_line)}\n')
    except IndexError:
        logging.error(f'`resume.items[0]` is not a valid index')


def portfolio_CLI_stringify(user_report: UserReport):
    '''
    Call the given `UserReport` object's `to_user_readable_string()`
    function and print it to the CLI

    Example Output:
    ```
    -----------------Portfolio------------------
    You started your first project on 6/15/2023!
    Your latest contribution was on 10/22/2025.
    Your coding languages: Python (70.80%), Typescript (24.63%), Javascript (2.76%), SQL (1.62%), CSS (0.14%), HTML (0.04%).
    User Ari Writing Score: 2.888479298179292
    --------------------------------------------
    ```
    '''
    portfolio = user_report.to_user_readable_string()

    if "\n" in portfolio:
        portfolio_header_len = len(portfolio.split('\n')[0])
        header_line = "Portfolio".center(portfolio_header_len, '-')
    else:
        # default to 20 if no portfolio is found
        header_line = "Portfolio".center(20, '-')

    print(header_line)
    print(portfolio)
    print('-' * len(header_line))
