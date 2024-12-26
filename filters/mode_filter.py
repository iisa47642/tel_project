from typing import Callable, Dict, Any, Awaitable, Union
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.filters import BaseFilter

def mode_filter(*modes: int):
    class ModeFilterImpl(BaseFilter):
        async def __call__(self, event: Union[Message, CallbackQuery], **kwargs) -> bool:
            current_mode = kwargs.get('current_mode')
            if current_mode is None:
                return False
            return current_mode in modes
    
    return ModeFilterImpl()