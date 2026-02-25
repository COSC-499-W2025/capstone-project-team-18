import os
import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from openai import OpenAI

from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)

# Type variable to handle dynamic Pydantic models
T = TypeVar('T', bound=BaseModel)


class AzureFoundryManager:
    """
    Handles connecting and routing requests to the Azure Foundry Model
    """

    def __init__(self):
        # "https://capstone-ai-resource.services.ai.azure.com/openai/v1/"
        self.endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
        self.api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
        self.deployment_name = os.getenv(
            "AZURE_FOUNDRY_DEPLOYMENT_NAME", "Phi-4")

        self.client = OpenAI(
            base_url=self.endpoint,
            api_key=self.api_key
        )

    def process_request(self, user_input: str, system_prompt: str, response_model: Type[T]) -> T:
        """
        Sends a prompt to the model, injects the Pydantic schema, and validates the JSON output.
        """
        schema_instructions = response_model.model_json_schema()

        full_system_prompt = (
            f"{system_prompt}\n\n"
            f"You must respond in valid JSON format matching this schema strictly: "
            f"{json.dumps(schema_instructions)}"
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"},
            )

            raw_content = completion.choices[0].message.content

            if raw_content is None:
                raise Exception()

            structured_response = response_model.model_validate_json(
                raw_content)

            return structured_response

        except ValidationError as e:
            # Pydantic catches hallucinations or wrong data types here
            logger.error(
                f"Validation Error: The model failed to return the correct data structure for {response_model.__name__}! {e}")
            raise
        except Exception as e:
            logger.error(f"API or Network Error processing request: {e}")
            raise
