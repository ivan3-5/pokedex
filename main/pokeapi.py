import requests
import random

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon/"

def get_pokemon(name_or_id):
	url = f"{POKEAPI_BASE_URL}{name_or_id}/"
	try:
		response = requests.get(url)
		response.raise_for_status()
		pokemon_data = response.json()

		if 'types' in pokemon_data:
			seen_types = set()
			unique_types = []
			
			for type_data in pokemon_data['types']:
				type_name = type_data['type']['name']
				if type_name not in seen_types:
					seen_types.add(type_name)
					unique_types.append(type_data)

			pokemon_data['types'] = unique_types
			
		return pokemon_data
	except requests.RequestException:
		return None

def search(query):
	url = "https://pokeapi.co/api/v2/pokemon?limit=10000"
	try:
		response = requests.get(url)
		response.raise_for_status()
		results = response.json().get("results", [])
		query_lower = query.lower()
		
		# Try to parse query as an ID if it's numeric
		is_numeric = query.isdigit()
		query_id = int(query) if is_numeric else None
		
		# Get types data to enable type searching
		all_types = get_all_types()
		matching_type_ids = []
		
		# Check if the query matches any type name
		for type_name, type_id in all_types.items():
			if query_lower in type_name.lower():
				matching_type_ids.append(type_id)
		
		# Initial matching by name
		matching_pokemon = []
		
		for p in results:
			pokemon_id = int(p["url"].split("/")[-2])
			
			# Match by name
			name_match = query_lower in p["name"].lower()
			
			# Match by ID (exact match)
			id_match = is_numeric and pokemon_id == query_id
			
			# Match by ID prefix (e.g., "25" matches "25", "250", "251", etc.)
			id_prefix_match = is_numeric and str(pokemon_id).startswith(query)
			
			if name_match or id_match or id_prefix_match:
				matching_pokemon.append({
					"name": p["name"],
					"id": pokemon_id
				})
		
		# If we have matching types and not too many results already, 
		# fetch Pokémon by type
		if matching_type_ids and len(matching_pokemon) < 100:
			type_matches = get_pokemon_by_types(matching_type_ids)
			
			# Add type matches to results if not already included
			existing_ids = {p["id"] for p in matching_pokemon}
			for pokemon in type_matches:
				if pokemon["id"] not in existing_ids:
					matching_pokemon.append(pokemon)
					existing_ids.add(pokemon["id"])
		
		return matching_pokemon
	except requests.RequestException as e:
		print(f"Error in search: {e}")
		return []

def get_all_types():
	"""Get a dictionary of all Pokémon types with their IDs."""
	url = "https://pokeapi.co/api/v2/type"
	types_dict = {}
	
	try:
		response = requests.get(url)
		response.raise_for_status()
		results = response.json().get("results", [])
		
		for type_data in results:
			type_name = type_data["name"]
			type_id = int(type_data["url"].split("/")[-2])
			
			# Only include actual Pokémon types (exclude "unknown" and "shadow")
			if type_id <= 18:  # Normal types have IDs 1-18
				types_dict[type_name] = type_id
		
		return types_dict
	except requests.RequestException:
		return {}

def get_pokemon_by_types(type_ids):
	"""Get Pokémon that have any of the specified types."""
	matching_pokemon = []
	
	for type_id in type_ids:
		try:
			url = f"https://pokeapi.co/api/v2/type/{type_id}"
			response = requests.get(url)
			response.raise_for_status()
			type_data = response.json()
			
			# Extract Pokémon from this type
			for pokemon_entry in type_data.get("pokemon", []):
				pokemon_url = pokemon_entry["pokemon"]["url"]
				pokemon_id = int(pokemon_url.split("/")[-2])
				pokemon_name = pokemon_entry["pokemon"]["name"]
				
				# Exclude forms and variants (typically have IDs > 10000)
				if pokemon_id < 10000:
					matching_pokemon.append({
						"name": pokemon_name,
						"id": pokemon_id
					})
		except requests.RequestException:
			continue
	
	return matching_pokemon

def get_random_pokemon(count=4, max_id=898):
	"""Get a list of random Pokémon. 
	Limits max_id to 898 to avoid getting forms and variants."""
	pokemon_ids = random.sample(range(1, max_id + 1), count)
	pokemon_list = []
	
	for pokemon_id in pokemon_ids:
		pokemon_data = get_pokemon(pokemon_id)
		if pokemon_data:
			pokemon_list.append(pokemon_data)
	
	return pokemon_list
