#!/usr/bin/env python

'''
Requires Python 3.7
'''

import requests, json, sys, pprint
from pathlib import Path
from utilities import utilities as u
from operator import itemgetter

'''

NOTE - if I am trying to associate a container with a location, do I 
also need to delete the current location of that container? NO because
I am just replacing the references - not actually appending a new
one unless it doesn't already have one.


This tool does the following:
1.) Looks up location barcodes and returns data about associated containers in ArchivesSpace
2.) Provides the option to update containers by:
	a.) Associating containers that are in a location but not currently associated with that location.
	b.) Unassociating containers that are not in a location but are currently associated with that location.

'''


####																			  ####
####	Functions to search locations and find their associated top containers    ####
####																			  ####

def search_locations(api_url, headers, location_barcode, location_uri=None, container_list=None):
	loc_search = requests.get(api_url + '/search?page=1&type[]=location&q=title:' + location_barcode, headers=headers).json()
	if loc_search['total_hits'] == 1:
		if location_barcode in loc_search['results'][0]['title']:
			location_uri = loc_search['results'][0]['uri']
			container_list = search_containers(api_url, headers, location_uri)
	else:
		#this means that either nothing was found or more than one barcode was found. Either way that is wrong.
		print(loc_search)
	return (location_uri, container_list)

def search_containers(api_url, headers, location_uri):
	containers = []
	query = f'{{"query":{{"jsonmodel_type": "field_query", "field": "location_uri_u_sstr", "value": "{location_uri}", "literal":true}}}}'
	tc_search = requests.get(api_url + "/repositories/12/top_containers/search?filter=" + query, headers=headers).json()
	if 'response' in tc_search:
		for item in tc_search['response']['docs']:
			#pprint.pprint(item)
			tc_uri = item['id']
			if 'barcode_u_sstr' in item:
				tc_barcode = item['barcode_u_sstr'][0]
			else:
				tc_barcode = 'missing_barcode'
			tc_data = item['title']
			#the HM films might need special treatment here...
			collection_id = item['collection_identifier_stored_u_sstr'][0]
			collection_title = item['collection_display_string_u_sstr'][0]
			collection_uri = item['collection_uri_u_sstr'][0]
			location_data = item['location_display_string_u_sstr'][0]
			indicator_data = item['display_string']
			#would also want to look up container profiles, but only if it's actually in the response
			data = [tc_data, collection_title, location_data, collection_id, tc_barcode, tc_uri, location_uri, collection_uri, indicator_data]
			containers.append(data)
	else:
		#this means that nothing was found? See what happens with more testing
		print(tc_search)
	if containers:
		containers = sorted(containers, key=itemgetter(8))
		display_container_data(containers)
	return containers

#want to be able to use the index to indicate containers in location but not found?
def display_container_data(containers):
	for i, container in enumerate(containers):
		tc_data = container[0]
		collection_title = container[1]
		location_data = container[2]
		print(i)
		print(tc_data)
		print(collection_title)
		print(location_data)
		print('\n')

####																					   		 ####
####	Functions to process and update barcodes not already associated with a given location    ####
####																					  		 ####	

def process_barcodes(api_url, headers, location_uri):
	print('''Welcome to the location update interface. Begin by scanning in the barcodes of the 
			containers you want to update. Enter DONE to finish''')
	'''This function allows users to scan in barcodes and'''
	done = False
	tc_barcodes = []
	while not done:
		tc_barcode = input('Container barcode: ')
		if tc_barcode == "DONE":
			done = True
			break
		else:
			tc_barcodes.append(tc_barcode)
	return tc_barcodes

def search_and_update(api_url, headers, tc_barcodes, location_uri):
	'''Loops through the list of barcodes '''
	for barcode in tc_barcodes:
		tc_uri = search_container_barcode(api_url, headers, barcode)
		if tc_uri != None:
			tc_json = location_update(api_url, headers, tc_uri, location_uri)
			tc_post = requests.post(api_url + tc_uri, headers=headers, json=tc_json).json()
			print(tc_post)
		else:
			print(f'Could not locate top container for barcode {barcode}')
			continue

def search_container_barcode(api_url, headers, barcode, tc_uri=None):
	'''Searches the ArchivesSpace API for a top container matching a given barcode'''
	search = requests.get(api_url + '/repositories/12/top_containers/search?q=barcode_u_sstr:' +  barcode, headers=headers).json()
	if 'response' in search:
		#also want to make sure that there is only one result
		for item in search['response']['docs']:
			tc_uri = item['id']
	return tc_uri

def location_update(api_url, headers, tc_uri, location_uri):
	tc_json = requests.get(api_url + tc_uri, headers=headers).json()
	#change this to real time calculation
	today = '2019-07-02'
	#I think it always is, just sometimes an empty list
	if 'container_locations' in tc_json:
		#check on this - again not sure if container location is always empty
		if len(tc_json['container_locations']) == 0:
			new_location = {'jsonmodel_type': 'container_location', 'ref': location_uri,
							'status': 'current', 'start_date': today}
			tc_json['container_locations'].append(new_location)
		if len(tc_json['container_locations']) == 1:
			tc_json['container_locations'][0]['ref'] = location_uri
			tc_json['container_locations'][0]['start_date'] = today
		else:
			#here need to find the correct location and change it. But I can't think of anythinhg
			#that has two locations, so I think I can skip for now?
			pass
	else:
		print('Key Error, container locations')
	return tc_json

####										   ####
#### 	Functions to Unassociate Containers    ####
####										   ####	

def unassociate_containers(api_url, headers, data):
	missing_containers = id_missing_containers()
	if missing_containers:
		not_found = [data[i] for i, container in enumerate(data) if i in missing_containers]
		for container in not_found:
			tc_uri, tc_json = unassociate_it(api_url, headers, container)
			tc_post = requests.post(api_url + tc_uri, headers=headers, json=tc_json).json()
			print(tc_post)

def id_missing_containers():
	#this doesn't work with more than one container
	which_ones = input('Please enter index number(s) or index range of missing boxes: ')
	if '-' in which_ones:
		which_ones = which_ones.split('-')
		which_ones = list(range(int(which_ones[0]), int(which_ones[1])))
	if len(which_ones) == 1:
		which_ones = [int(which_ones)]
	if len(which_ones) > 1 and type(which_ones) is not list:
		which_ones = [int(item) for item in which_ones.split(' ')]
	return which_ones

def unassociate_it(api_url, headers, container):
	tc_uri = container[5]
	location_uri = container[6]
	tc_json = requests.get(api_url + tc_uri, headers=headers).json()
	#this filters out locations which match the uri; I like this approach and
	#should use it when I delete the grandchildren as well; and any other time I want to
	#filter a list. duh
	container_locations = [container_loc for container_loc in tc_json['container_locations']
							if 'ref' in container_loc and container_loc['ref'] != location_uri]
	tc_json['container_locations'] = container_locations
	return (tc_uri, tc_json)

####				     ####
####	Write output     ####
####					 ####

#should I also write output of new locations?
def write_output(data, enum_value, output_file):
	header_row = ['tc_data', 'collection_title', 'location_data', 'collection_id', 'tc_barcode', 'tc_uri', 'location_uri', 'collection_uri', 'MISSING']
	fileobject, csvoutfile = u.opencsvout(output_file)
	#if there is more than one barcode to search, this line prevents the header row from being written each time.
	if enum_value == 1:
		csvoutfile.writerow(header_row)
	csvoutfile.writerows(data)
	fileobject.close()

####					 ####
#### 	Main Function    ####
####					 ####	

def main():
	home_dir = str(Path.home())
	config_file = u.get_config(cfg=home_dir + '\\config.yml')
	api_url, headers = u.login(url=config_file['api_url'], username=config_file['api_username'], password=config_file['api_password'])
	print(f'Connected to {api_url}')
	output_file = config_file['api_output_csv']
	print('Welcome to the location barcode lookup tool. Scan barcodes below. Enter QUIT to exit.')
	done = False
	x = 0
	while not done:
		x += 1
		barcode = input('Location barcode: ')
		if barcode == 'QUIT':
			break
		else:
			location_uri, data = search_locations(api_url, headers, barcode)
			#will need to change this again so header row is not repeated
			write_output(data, x, output_file)
			print('Would you like to add containers to this location? Enter Y or N.')
			decision = input('Y/N: ')
			if decision == 'Y':
				#this pulls the location URI for the barcode
				barcode_list = process_barcodes(api_url, headers, location_uri)
				search_and_update(api_url, headers, barcode_list, location_uri)
			elif decision == 'N':
				pass
			print('Would you like to remove containers from this location? Enter Y or N.')
			decision_2 = input('Y/N: ')
			if decision_2 == 'Y':
				unassociate_containers(api_url, headers, data)
			elif decision_2 == 'N':
				pass


'''
What to do about boxes that SHOULD be in a location but arent? need a way to ID. Right now have an extra column in the spreadsheet where
this can be marked by hand during a survey. But also then need to remove the container from that location. This should be 
another function, but I don't know if I want to do that automatically, or exactly how that would be implemented.

Also want to be able to update containers which do not have barcodes. 

'''

if __name__ == "__main__":
	main()