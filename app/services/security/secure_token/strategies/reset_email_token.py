from app.services.security.secure_token.strategies.base_strategy import ITokenStrategy
from datetime import timedelta

class ResetEmailTokenStrategy(ITokenStrategy):
    
    def _get_default_expiry(self) -> timedelta:
        return timedelta(hours=1)
    
    async def create_token(
            self, 
            data, 
            expire_delta = None
        ) ->str:
        return self._encode_token(
            data,
            'reset_email_token',
            expire_delta)
    
    async def decode_token(self, token) -> dict:
        return self._decode_token(token, 'reset_email_token')
    