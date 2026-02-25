from pydantic import BaseModel


class ReadmeKeywordOutput(BaseModel):
    tool_keywords: list[str]
    task_keywords: list[str]
    tone: str


EXTRACTION_PROMPT = """
You are a README extraction assistant. You are going to be given a README file from the user. Your task is
to extracted and respond in structured output the following information.

The first field is called 'tool_keywords'. It will be a list of strings that deal with the frameworks and tools
that this README talks about. Keywords that are tech facing.

The second field is called 'task_keywords'. This field will be a list of strings that deal with the problem that the
README is trying to solve. It is user facing and shouldn't include tech details. Rather, it should include keywords
about the domain of the project as a solution to a problem.

The third field is called 'tone'. The tone is a string that describes the overall tone of the project. Some examples include
'Professional', 'Educational', or 'Experimental'. Tone is always one word, and starts with a capital letter.
"""
