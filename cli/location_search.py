#!/usr/bin/env python

'''
Requires Python 3.7
'''

import requests, json, sys, pprint
from pathlib import Path
from utilities import utilities as u

def search_locations(api_url, headers, location_barcode):
	loc_search = requests.get(api_url + '/search?page=1&type[]=location&q=title:' + location_barcode, headers=headers).json()
	if loc_search['total_hits'] == 1:
		if location_barcode in loc_search['results'][0]['title']:
			location_uri = loc_search['results'][0]['uri']
			container_list = search_containers(api_url, headers, location_uri)
	else:
		#this means that either nothing was found or more than one barcode was found. Either way that is wrong.
		container_list = None
		print(loc_search)
	return container_list

def search_containers(api_url, headers, location_uri):
	containers = []
	query = f'{{"query":{{"jsonmodel_type": "field_query", "field": "location_uri_u_sstr", "value": "{location_uri}", "literal":true}}}}'
	tc_search = requests.get(api_url + "/repositories/12/top_containers/search?filter=" + query, headers=headers).json()
	if 'response' in tc_search:
		for item in tc_search['response']['docs']:
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
			#would also want to look up container profiles, but only if it's actually in the response
			data = [tc_uri, tc_barcode, tc_data, collection_id, collection_title, collection_uri, location_data, location_uri]
			print(data)
			containers.append(data)
	else:
		#this means that nothing was found? See what happens with more testing
		print(tc_search)
	return containers

def write_output(data, enum_value, output_file):
	header_row = ['tc_uri', 'tc_barcode', 'tc_data', 'collection_id', 'collection_title', 'collection_uri', 'location_data']
	fileobject, csvoutfile = u.opencsvout(output_file)
	#if there is more than one barcode to search, this line prevents the header row from being written each time.
	if enum_value == 0:
		csvoutfile.writerow(header_row)
	csvoutfile.writerows(data)
	fileobject.close()

def main():
	home_dir = str(Path.home())
	config_file = u.get_config(cfg=home_dir + '/config.yml')
	api_url, headers = u.login(url=config_file['api_url'], username=config_file['api_username'], password=config_file['api_password'])
	output_file = config_file['api_output_csv']
	#want to be able to do this more than once - ORRR just have this as a command line argument like the dupe detect
	if len(sys.argv) > 1:
		barcodes = sys.argv[1:]
		for i, barcode in enumerate(barcodes):
			data = search_locations(api_url, headers, barcode)
			#need to fix this so that if there's already a header row don't create another one
			write_output(data, i, output_file)

if __name__ == "__main__":
	main()