from fastapi import APIRouter
from pydantic import BaseModel

from algorithms import set_weather, get_weather


router = APIRouter(prefix="/api/weather", tags=["weather"])


class WeatherPayload(BaseModel):
    weather: str


@router.post("/set")
def set_weather_endpoint(payload: WeatherPayload):
    """
    更新当前天气状态。

    允许值：sunny / rain / snow / fog
    """
    set_weather(payload.weather)
    return {"weather": get_weather()}

