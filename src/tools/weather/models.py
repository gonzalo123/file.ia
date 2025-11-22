from datetime import datetime

from pydantic import BaseModel, Field


# Meteorological reading models
class TemperatureReading(BaseModel):
    """Temperature reading at 2 meters"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(description="Temperature in °C")


class HumidityReading(BaseModel):
    """Relative humidity reading at 2 meters"""
    time: datetime = Field(..., description="Timestamp")
    value: int = Field(..., ge=0, le=100, description="Relative humidity in %")


class ApparentTemperatureReading(BaseModel):
    """Apparent temperature reading"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., description="Apparent temperature in °C")


class PrecipitationReading(BaseModel):
    """Precipitation reading"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., ge=0, description="Precipitation in mm")


class EvapotranspirationReading(BaseModel):
    """Evapotranspiration reading"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., description="Evapotranspiration in mm")


class SurfacePressureReading(BaseModel):
    """Surface pressure reading"""
    time: datetime = Field(..., description="Timestamp")
    value: float = Field(..., gt=0, description="Surface pressure in hPa")


class MeteoData(BaseModel):
    """Model to store meteorological data"""
    temperature: list[TemperatureReading] = Field(..., description="List of temperature readings")
    humidity: list[HumidityReading] = Field(..., description="List of humidity readings")
    apparent_temperature: list[ApparentTemperatureReading] = Field(..., description="List of apparent temperature readings")
    precipitation: list[PrecipitationReading] = Field(..., description="List of precipitation readings")
    evapotranspiration: list[EvapotranspirationReading] = Field(..., description="List of evapotranspiration readings")
    surface_pressure: list[SurfacePressureReading] = Field(..., description="List of surface pressure readings")
