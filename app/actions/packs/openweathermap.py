from ..schema import ActionPack, auth, secure
from pydantic import BaseModel, Field
import requests


class Coordinates(BaseModel):
    longitude: float
    latitude: float


class WeatherCondition(BaseModel):
    condition: str
    description: str
    icon: str


class Temperature(BaseModel):
    current: float
    feels_like: float
    min: float
    max: float


class Wind(BaseModel):
    speed: float
    direction: int
    gust: float


class Location(BaseModel):
    name: str
    coordinates: Coordinates
    country: str


class WeatherSummary(BaseModel):
    location: Location
    weather: WeatherCondition
    temperature: Temperature
    humidity: int
    wind: Wind
    clouds: int = Field(..., description="Percentage of cloud cover")
    visibility: int = Field(..., description="Visibility in meters")


@auth(keys=["OPENWEATHERMAP_API_KEY"])
class OpenWeatherMap(ActionPack):
    @secure
    def get_current_weather(self, city_name: str) -> WeatherSummary:
        lat, lon = self.get_lat_lon(city_name)
        api_key = self.auth["OPENWEATHERMAP_API_KEY"]
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = f"{base_url}appid={api_key}&lat={lat}&lon={lon}"
        response = requests.get(complete_url)
        return response.json()

    @secure
    def get_lat_lon(self, city_name: str) -> Coordinates:
        # TODO: Improve geocoding
        api_key = self.auth["OPENWEATHERMAP_API_KEY"]

        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = f"{base_url}q={city_name}&appid={api_key}"

        response = requests.get(complete_url)
        data = response.json()

        if data["cod"] != 200:
            raise Exception(f"Error: {data['message']}")

        return Coordinates(
            latitude=data["coord"]["lat"], longitude=data["coord"]["lon"]
        )
