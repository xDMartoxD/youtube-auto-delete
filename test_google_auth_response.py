# Test para verificar el problema con GoogleAuthResponse

# Respuesta de Google que está fallando:
google_response = {
    'access_token': 'ya29.a0ATi6K2uYNjBuaGukaSNeFOFx-HK2Wtqt9JwAGlqN1nEYIv5e5lzyfdCj8-Ne-nyDxnIToLLm4Hc43TUwH1eIr19V3GzD_MiE26kQOOwWIR_kr_Qma5DySTrpFALIbp-VjV5HRREV2twOLZ5ZtcjkbBnSI2e59wNvbhondt--UU5n981kDwq4IK4LCsAcmfRKj14_xWdnaCgYKAd4SARUSFQHGX2Mimn13XWzkyLqSw2lZKV_mpQ0207',
    'expires_in': 3599,
    'scope': 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/youtube openid',
    'token_type': 'Bearer',
    'id_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6Ijg4NDg5MjEyMmUyOTM5ZmQxZjMxMzc1YjJiMzYzZWM4MTU3MjNiYmIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIxMDQ1NjAyNDEzNjU5LW5zNmNxMjdvaTdybzF2ajlwZDltOGJpcTdxNTlqMjU5LmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwiYXVkIjoiMTA0NTYwMjQxMzY1OS1uczZjcTI3b2k3cm8xdmo5cGQ5bThiaXE3cTU5ajI1OS5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbSIsInN1YiI6IjEwNjcxNDY4MjY4NzIwNDU5MDYzNCIsImVtYWlsIjoibWFydGlucmVzdHJlcG8yMDAwQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJhdF9oYXNoIjoid1dJdHAyM01fMWhsNWY5S1d0WnZLQSIsImlhdCI6MTc2MTUyMjk3NywiZXhwIjoxNzYxNTI2NTc3fQ.C8XHS5l3RNYd_OEhqhtDIEJzCb34zi45ihB8tyqebFP8LjksT5MadZFlF0gSEOAPGgkmsapa2PnG0Z9KkyxJxMsNr7LJoLKcJUkqdg_dmIIPZijBE41XN3nX88HErhOlJ7_nXpbLP0mFqkvWYaOYFOh_TgPLC2akrTa_G2DVDpu1o00J_e5MKfDpQqc6Tm4YD0sfOTcJVcRtnOYor-GvWVHmADcNp4tX94E0AtSUKxJqPn5ih8sFFjAABJzTfCfMqmOM3nJWxNWuZCgDDkrAnq5eoYv0EhQotiU85csnJTeX-7wR2xZBAyggzhSbDBlrjdRTf7_dobfRxWzMoGjAoQ',
    'refresh_token_expires_in': 582899
}

# El modelo GoogleAuthResponse:
class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None  # ✅ Opcional
    expires_in: int
    token_type: str
    refresh_token_expires_in: int
    id_token: str
    model_config = {"extra": "allow"}

# Test de validación:
try:
    response = GoogleAuthResponse.model_validate(google_response)
    print("✅ Validación exitosa!")
    print(f"refresh_token: {response.refresh_token}")
except Exception as e:
    print(f"❌ Error de validación: {e}")
