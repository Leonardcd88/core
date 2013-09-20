from datetime import datetime, timedelta

from app.observer.Timer import track_time_change

STATE_DEVICE_NOT_HOME = 'device_not_home'
STATE_DEVICE_HOME = 'device_home'

STATE_DEVICE_DEFAULT = STATE_DEVICE_NOT_HOME

# After how much time do we consider a device not home if
# it does not show up on scans
# 70 seconds is to ensure 2 scans
TIME_SPAN_FOR_ERROR_IN_SCANNING = timedelta(seconds=70)

STATE_CATEGORY_ALL_DEVICES = 'device.alldevices'
STATE_CATEGORY_DEVICE_FORMAT = 'device.{}'


class DeviceTracker:

	def __init__(self, eventbus, statemachine, device_scanner):
		self.statemachine = statemachine
		self.eventbus = eventbus
		self.device_scanner = device_scanner

		default_last_seen = datetime(1990, 1, 1)

		temp_devices_to_track = device_scanner.get_devices_to_track()

		self.devices_to_track = { device: { 'name': temp_devices_to_track[device],
											'last_seen': default_last_seen,
											'category': STATE_CATEGORY_DEVICE_FORMAT.format(temp_devices_to_track[device]) }
								  for device in temp_devices_to_track }

		self.all_devices_state = STATE_DEVICE_DEFAULT

		# Add categories to state machine
		statemachine.add_category(STATE_CATEGORY_ALL_DEVICES, STATE_DEVICE_DEFAULT)

		for device in self.devices_to_track:
			self.statemachine.add_category(self.devices_to_track[device]['category'], STATE_DEVICE_DEFAULT)

		track_time_change(eventbus, lambda time: self.update_devices(device_scanner.scan_devices()))


	def device_state_categories(self):
		for device in self.devices_to_track:
			yield self.devices_to_track[device]['category']


	def set_state(self, device, state):
		if state == STATE_DEVICE_HOME:
			self.devices_to_track[device]['last_seen'] = datetime.now()

		self.statemachine.set_state(self.devices_to_track[device]['category'], state)


	def update_devices(self, found_devices):
		# Keep track of devices that are home, all that are not will be marked not home
		temp_tracking_devices = self.devices_to_track.keys()

		for device in found_devices:
			# Are we tracking this device?
			if device in temp_tracking_devices:
				temp_tracking_devices.remove(device)

				self.set_state(device, STATE_DEVICE_HOME)

		# For all devices we did not find, set state to NH
		# But only if they have been gone for longer then the error time span
		# Because we do not want to have stuff happening when the device does
		# not show up for 1 scan beacuse of reboot etc
		for device in temp_tracking_devices:
			if self.statemachine.get_state(self.devices_to_track[device]['category']).state == STATE_DEVICE_HOME and \
				datetime.now() - self.devices_to_track[device]['last_seen'] > TIME_SPAN_FOR_ERROR_IN_SCANNING:

				self.set_state(device, STATE_DEVICE_NOT_HOME)


		# Get the set of currently used statuses
		states_of_devices = [self.statemachine.get_state(self.devices_to_track[device]['category']).state for device in self.devices_to_track]

		self.all_devices_state = STATE_DEVICE_HOME if STATE_DEVICE_HOME in states_of_devices else STATE_DEVICE_NOT_HOME

		self.statemachine.set_state(STATE_CATEGORY_ALL_DEVICES, self.all_devices_state)
