import logging
from datetime import timedelta
from itertools import chain

from homeassistant.const import TEMP_CELSIUS
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

from ruuvitag_sensor.ruuvi import RuuviTagSensor
from ruuvitag_sensor.ruuvitag import RuuviTag

REQUIREMENTS = ['ruuvitag-sensor==0.8.0']


class ThrottledRuuviTag(RuuviTag):
    @Throttle(min_time=timedelta(seconds=60))
    def update(self, *args, **kwargs):
        return super().update(*args, **kwargs)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    SENSOR_TYPES = {
        'pressure': PressureRuuviTagSensor,
        'temperature': TemperatureRuuviTagSensor,
        'humidity': HumidityRuuviTagSensor
    }
    sensors = {}

    # Add configured sensors.
    for name, sensor_config in config['sensors'].items():
        mac = sensor_config['mac']
        sensors[mac] = tuple((SENSOR_TYPES[t](mac, name)
            for t in sensor_config.get('datas', SENSOR_TYPES.keys())))

    # Auto discover ruuvitags.
    if config.pop('discover', True):
        ruuvitags = RuuviTagSensor.get_data_for_sensors(search_duratio_sec=5)
        # Drop configured sensors from found ones
        for mac in sensors:
            ruuvitags.pop(mac)

        # Name found tags with identifier. Add sensor for every data fields. 
        for mac, data in ruuvitags.items():
            identifier = data.pop('identifier', 'unknown')
            sensors[mac] = tuple((SENSOR_TYPES[data_type](mac, identifier)
                for t in data))
    add_devices(list(chain(*sensors.values())))


class BaseRuuviTagSensor(Entity):
    sensors = {}
    def __init__(self, mac, name):
        """Initialize the sensor."""
        self._mac = mac
        self._name = name
        if not mac in self.sensors:
            sensor = ThrottledRuuviTag(mac)
            sensor.update()
            self.sensors[mac] = sensor

    @property
    def sensor_type(self):
        raise NotImplemented()

    @property
    def sensor(self):
        return self.sensors[self._mac]

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._name, self.sensor_type.title())

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.sensor.state[self.sensor_type]

    @property
    def unit_of_measurement(self):
        raise NotImplemented()

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.sensor.update()


class TemperatureRuuviTagSensor(BaseRuuviTagSensor):
    @property
    def sensor_type(self):
        return 'temperature'

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS


class HumidityRuuviTagSensor(BaseRuuviTagSensor):
    @property
    def sensor_type(self):
        return 'humidity'

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return '%'


class PressureRuuviTagSensor(BaseRuuviTagSensor):
    @property
    def sensor_type(self):
        return 'pressure'

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return 'hPa'
