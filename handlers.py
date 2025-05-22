from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(F.text.lower().contains("работаешь?"))
async def question(message: Message):
    await message.answer("Работаю.")