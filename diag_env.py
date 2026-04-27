from src.config.settings import get_settings
import httpx

s = get_settings()
print('OPENAI_CONFIGURED=', bool(s.openai_api_key))
print('GEMINI_CONFIGURED=', bool(s.gemini_api_key))
print('DEFAULT_MODEL=', s.default_model)
from src.services.llm_service import LLMService
svc = LLMService(settings=s)
print('CHOSEN_PROVIDER=', svc._choose_provider(None))

if s.openai_api_key:
    headers = {'Authorization': f'Bearer {s.openai_api_key}'}
    try:
        r = httpx.get('https://api.openai.com/v1/models', headers=headers, timeout=15.0)
        print('OPENAI_MODELS_STATUS=', r.status_code)
        txt = r.text
        print('RESPONSE_LEN=', len(txt))
        low = txt.lower()
        if 'insufficient_quota' in low or 'quota' in low or 'error' in low:
            print('RESPONSE_CONTAINS_ERROR_SUMMARY')
        else:
            print('RESPONSE_OK_SUMMARY')
    except Exception as e:
        print('OPENAI_PROBE_ERROR=', repr(e))
else:
    print('OPENAI_KEY_MISSING')
