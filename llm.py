# import os
# from openai import OpenAI

# client = OpenAI(
#     api_key=os.environ["OPENROUTER_API_KEY"],
#     base_url="https://openrouter.ai/api/v1"
# )

# def call_llm(system: str, user: str, model="nvidia/nemotron-4-340b"):
#     response = client.chat.completions.create(
#         model=model,
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user", "content": user},
#         ],
#     )
#     return response.choices[0].message.content

# import os
# from openai import OpenAI

# def get_client():
#     return OpenAI(
#         api_key=os.environ["OPENROUTER_API_KEY"],
#         base_url="https://openrouter.ai/api/v1",
#     )

# def call_llm(system, user, model="nvidia/nemotron-4-340b-instruct"):
#     client = get_client()

#     response = client.chat.completions.create(
#         model=model,
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user", "content": user},
#         ],
#     )

#     return response.choices[0].message.content

import os
from openai import OpenAI

def get_client():
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )

def call_llm(system: str, user: str, model="openai/gpt-4o-mini"):
    client = get_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    return response.choices[0].message.content
