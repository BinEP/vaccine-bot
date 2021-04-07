from discord.ext import tasks
from openlocationcode import openlocationcode as olc
import requests
import json
import math as m

import discord


class MyClient(discord.Client):
	lastData = ""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		# an attribute we can access from our task
		self.counter = 0
		
		# start the task to run in the background
		self.my_background_task.start()
		
		self.previous_bundle = {}
		
		self.filter_results = [("Walmart", "Buffalo", ["moderna"])]
		self.filter_targets = []
		with open("cities.txt", "r") as file:
			self.target_cities = [city.lower() for city in file.readlines()]
		self.targets = [("Mpls", (44.97621, -93.25916), 50.), ("Cabin", (redacted), 40.)]
	
	async def on_ready(self):
		print('Logged in as')
		print(self.user.name)
		print(self.user.id)
		print('------')
	
	@tasks.loop(seconds=30)  # task runs every 30 seconds
	async def my_background_task(self):
		channel = self.get_channel(828332615315488789)  # channel ID goes here
		
		data = json.loads(requests.get("https://www.vaccinespotter.org/api/v0/states/MN.json").text)
		if data is None or data["features"] is None:
			return
		
		bundle_targets = {}
		for f in data["features"]:
			if f["properties"]["appointments_available"]:
				lat = f["geometry"]["coordinates"][1]
				lon = f["geometry"]["coordinates"][0]
				
				valid, targets = self.is_valid_location(lat, lon, f["properties"]["city"])
				if valid:
					vaccine_types = f["properties"]["appointment_vaccine_types"] or {}
					vaccine_types = [key for key in vaccine_types if vaccine_types[key]]  # Try saying that 10 times fast
					if any(f["properties"]["provider_brand_name"] == provider and f["properties"]["city"] == city and vaccine_types == types for provider, city, types in self.filter_results):
						continue
					if any(filter_target in targets for filter_target in self.filter_targets):
						continue
					
					tag = "<@369612437441347594>" if "Cabin" in targets else "<@&828333792557006909>"
					log_str = "New Vaccines %s at %s in %s (plus: %s  zip: %s  targets: [%s])" % (
						str(vaccine_types),
						f["properties"]["provider_brand_name"],
						f["properties"]["city"],
						olc.encode(lat, lon, codeLength=8),
						f["properties"]["postal_code"],
						", ".join([targets[key] for key in targets]) if targets is not None else "unknown")
					
					url = f["properties"]["url"] or "https://www.vaccinespotter.org/MN/"
					print(log_str)
					if tag not in bundle_targets:
						bundle_targets[tag] = tag + "\n"
					bundle_targets[tag] = bundle_targets[tag] + "%s\n<%s>\n" % (log_str, url)
		
		if len(bundle_targets) > 0 or len(self.previous_bundle) > 0:
			output = "---------\n"
			send_output = False
			for tag in self.previous_bundle:
				if tag not in bundle_targets:
					output += tag + "\nVaccines are gone\n"
					send_output = True
			for tag in bundle_targets:
				if tag in self.previous_bundle:
					if bundle_targets[tag] != self.previous_bundle[tag]:
						output += bundle_targets[tag]
						send_output = True
				else:
					output += bundle_targets[tag]
					send_output = True
			if send_output:
				await channel.send(output)
		self.previous_bundle = bundle_targets

	@my_background_task.before_loop
	async def before_my_task(self):
		await self.wait_until_ready()  # wait until the bot logs in
	
	def is_valid_location(self, lat, lon, city):
		matching_locations = {}
		if lat is not None and lon is not None:
			for target_name, target_latlon, target_maxdist in self.targets:
				distance = self.get_distance((lat, lon), target_latlon)
				if distance < target_maxdist:
					matching_locations[target_name] = "%s: %.2f mi" % (target_name, distance)
			if len(matching_locations) > 0:
				return True, matching_locations
		
		if city is not None and city.lower() in self.target_cities:
			return True, None
		return False, None
	
	@staticmethod
	def get_distance(point1, point2):
		radius = 3958.7559152  # miles
		lat1 = m.radians(point1[0])
		lon1 = m.radians(point1[1])
		lat2 = m.radians(point2[0])
		lon2 = m.radians(point2[1])
		
		dlon = lon2 - lon1
		dlat = lat2 - lat1
		
		a = m.sin(dlat / 2) ** 2 + m.cos(lat1) * m.cos(lat2) * m.sin(dlon / 2) ** 2
		c = 2 * m.atan2(m.sqrt(a), m.sqrt(1 - a))
		distance = radius * c
		return distance


client = MyClient()
client.run('ODI4MzI5NDUwMDU5MzMzNjMy.YGn_6g.vORB9Bnu6vhWC97wdV-lEhYIAWI')
