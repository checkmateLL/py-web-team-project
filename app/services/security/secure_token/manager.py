from typing import Optional
from app.services.security.secure_token.types import TokenType
from app.services.security.secure_token.strategies import (
    AccessTokenStrategy,
    RefreshTokenStrategy,
)

class TokenStrategyFactory:

    _strategies = {
        TokenType.ACCESS: AccessTokenStrategy,
        TokenType.REFRESH: RefreshTokenStrategy,
    }

    @classmethod
    def get_strategy(cls, token_type: TokenType):
        strategy_class = cls._strategies.get(token_type)
        if not strategy_class:
            raise ValueError(
                f'Unsupported token type: {token_type}'
            )
        return strategy_class() # type:ignore

class TokenManager:
    def __init__(
            self, 
            strategy_factory: TokenStrategyFactory = TokenStrategyFactory()
        ):
        self.strategy_factory = strategy_factory

    async def create_token(
            self, 
            token_type: TokenType, 
            data: dict, 
            expire_delta: Optional[float] = None
        ) -> str:
        strategy = self.strategy_factory.get_strategy(token_type)
        return await strategy.create_token(data, expire_delta)
    
    async def decode_token(self, token_type: TokenType, token: str) -> dict:
        strategy = self.strategy_factory.get_strategy(token_type)
        return await strategy.decode_token(token)

token_manager = TokenManager()