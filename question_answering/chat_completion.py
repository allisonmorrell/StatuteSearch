import openai

from openai.error import APIError, ServiceUnavailableError, Timeout

from tenacity import retry, retry_if_exception_type, wait_random_exponential, stop_after_attempt

exceptions_list = (APIError, Timeout, ServiceUnavailableError)

@retry(
    retry=retry_if_exception_type(exceptions_list),
    wait=wait_random_exponential(min=1, max=5), 
    stop=stop_after_attempt(3),
)
def chat_completion_request(**kwargs):
    response = openai.ChatCompletion.create(**kwargs)
    return response