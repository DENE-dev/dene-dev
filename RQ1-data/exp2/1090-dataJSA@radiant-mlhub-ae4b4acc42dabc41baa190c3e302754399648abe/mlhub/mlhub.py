import re
import tqdm
import arrow
import boto3
from retry_requests import retry
from requests import Session

from mlhub import logger

import os
from pathlib import Path
from urllib.parse import urlparse
from itertools import chain
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool


class Client(object):
    """Radiant MLHub Client.

    Parameters:
        api_token (str, optional): MLHub API token . Defaults to os.getenv('MLHUB_ACCESS_TOKEN').
        boto_client (str, optional): Parameter to initialize AWS (S3) client. Defaults to 's3'.
        threads (int, optional): Default number of threads to be used by the multithreaded methods.
        Defaults to None.
        collection_id (str, optional): One of the collection id available on the Radiant MLHub.
        Defaults to 'ref_landcovernet_v1_labels'.
        feature_id (str, optional): One of the feature id belonging to the collection. Defaults to None.

    Attributes:
        base_url (str): Radiant MLHub base URL.
        headers (dict): Request headers.
        collection_uri (str): URI of the default collection object.
        collection_items_uri (str): URI of the default paginated items collection.
        collection_feature_uri (str): URI of the default collection item.
        crawler_position (dict): Crawler page.
        assets_fetched (list): List of the fetched assets.
        assets_downloaded (list): List of the downloaded assets.
    """

    def __init__(self,
                 api_token=os.getenv('MLHUB_ACCESS_TOKEN'),
                 boto_client='s3',
                 threads=None,
                 collection_id='ref_landcovernet_v1_labels',
                 feature_id=None):

        self.api_token = api_token
        self.boto_client = boto3.client(boto_client)
        self.threads = threads
        self.collection_id = collection_id
        self.feature_id = feature_id
        self.base_url = 'http://api.radiant.earth/mlhub/v1'
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_token}'
        }
        self.collection_uri = self.base_url + f'/collections/{collection_id}'
        self.collection_items_uri = self.base_url + f'/collections/{collection_id}/items'
        self.collection_feature_uri = self.base_url + f'/collections/{collection_id}/items/{feature_id}'
        logger.info(f'\
\nCreate MLHub API client for collection {collection_id}.\n \
API Token provided = {True if api_token is not None else False}.')
        self.crawler_position = {'page': None, 'feature_id': None, 'uri': None}
        self.assets_fetched = []
        self.assets_downloaded = []

    def _get_uri(self, uri, **kwargs):
        """Retrives the content of an URI request.

        The `_get_uri` method configures a session to retry on failed requests
        due to server connection errors, HTTP answer (500, 502, 504). The method will
        perform 5 retries. A backoff factor of 0.5 will be applied between each retries
        (sleep times [0.0, 0.5, 1.0, 1.5, 2.0]). If the server does not respond after 5 secondes
        the method will raise an error.

        Args:
            uri (str): URI to request

        Returns:
            (bytes, NoneType): Request response None if an error is raised.
        """
        session = retry(Session(), retries=5, backoff_factor=0.5)

        try:
            response = session.get(uri, **kwargs)
            if response.status_code in (200, 302, 401):
                return response
        except Exception as e:
            logger.exception(f" \n {100*'='} \n {e} \n {100*'='}")
            return None

    def _get_download_uri(self, uri):
        """Retrieves the download URI of an item from its hyperlink.

        Args:
            uri (str): Reference URI to request

        Returns:
            (str, NoneType): Download URI None if an error is raised.
        """

        response = self._get_uri(uri, allow_redirects=False, headers=self.headers)
        # TODO correct Logic issue response has not attribute get
        # response.headers.
        if response is not None:
            download_uri = response.headers.get('Location')
        else:
            download_uri = None
            logger.info(f"\n The Server is unable to return a download uri given the reference URI: \n {uri}")

        return download_uri

    def _download_bucket(self, uri, path):
        """Downloads an asset hosted on s3 bucket in a specific location.

        Args:
            uri (str): Download URI.
            path (str): Destination file.
        """
        parsed = urlparse(uri)
        bucket = parsed.netloc
        key = parsed.path[1:]
        self.boto_client.download_file(bucket, key, os.path.join(path, key.split('/')[-1]))

    def _download_http(self, uri, path):
        """Downloads an asset hosted on an http server in a specific location.

        Args:
            uri (str): Download URI.
            path (str): Destination file.
        """
        parsed = urlparse(uri)
        response = self._get_uri(uri)
        if response is not None:
            with open(os.path.join(path, parsed.path.split('/')[-1]), 'wb+') as f:
                for chunk in response.iter_content(chunk_size=512 * 1024):
                    if chunk:
                        f.write(chunk)

    def _multiprocess(self, function, iterable, threads=None, leave=True):
        """Multithreading method wrapper to parallelize functions on multiple threads.

        Args:
            function (Callable): single threaded function.
            iterable (lint): list of single threaded function's parameters.
            threads (int, optional): Number of threads. Defaults to None.
            leave (bool, optional): Whether to left tqdm output after task is finished. Defaults to True.

        Notes:
             If threads is None the number of threads default to min(32, os.cpu_count() + 4).
             This default value preserves at least 5 workers for I/O bound tasks and utilizes at most
             32 CPU cores for CPU bound tasks which release the GIL (Concurrent future 3.8).
        """
        threads = self.threads if threads is None else threads

        if threads is None:
            threads = min(32, cpu_count() + 4)
        if threads < 2:
            results = [function(item) for item in tqdm.tqdm(iterable, total=len(iterable), leave=leave)]
        else:
            with ThreadPool(threads) as tp:
                results = list(tqdm.tqdm(tp.imap(function, iterable), total=len(iterable), leave=leave))
        if any([o is not None for o in results]):
            return results

    def describe_collection(self):
        """Returns collection description.
        """
        response = self._get_uri(self.collection_uri, headers=self.headers)
        if response is not None:
            collection = response.json()
            print(f"\
Description of the MLHubClient object collection: \n \n\
* Collection NAME: {collection.get('description')} \n\
* Collection ID: {collection.get('id')} \n\
* Collection ITEMS URL: {collection.get('links')[3].get('href')} \n\
* Collection spatial coverage: \n {collection.get('extent').get('spatial').get('bbox')} \n\
* Collection time coverage: \n {collection.get('extent').get('temporal').get('interval')} \n\
* Collection DOI: {collection.get('sci:doi')} \n\
* Collection Citation: \n {collection.get('sci:citation')} \n\
* Collection Licence: {collection.get('licence')} \n"
                  )

    def get_item(self, collection_id=None, item_id=None):
        """Retrieves `item_id` item from `collection_id` collection.

        Args:
            collection_id (str, optional): collection id e.g `ref_landcovernet_v1_labels`. Defaults to None.
            item_id (str, optional): item id e.g `ref_landcovernet_v1_labels_29PKL_19`. Defaults to None.

        Returns:
            [dict]: returns item response document json as a dictionary list containing the following
            attributes ('assets', 'bbox', 'collection',  'geometry', 'id', 'links', 'properties',
            'stac_extensions', 'type').
        """

        collection = self.collection_id if collection_id is None else collection_id
        item = self.feature_id if item_id is None else item_id
        feature_uri = self.base_url + f'/collections/{collection}/items/{item}'

        response = self._get_uri(feature_uri, headers=self.headers)
        if response is not None:
            return response.json()
        else:
            return None
        #return (path, item_download_ref)

    def get_items(self, collection_id=None, items_ids=None):
        """Retrieves all items in `items_ids` from the `collection_id` collection.

        Args:
            collection_id (str, optional): collection id e.g `ref_landcovernet_v1_labels`. Defaults to None.
            items_id (list): item id e.g `ref_landcovernet_v1_labels_29PKL_19`. Defaults to None.


        Returns:
            [list[dict]]: returns items response documents json as a dictionary list containing the following
            attributes ('assets', 'bbox', 'collection',  'geometry', 'id', 'links', 'properties',
            'stac_extensions', 'type').
        """
        collection_id = self.collection_id if collection_id is None else collection_id
        items_ids = [self.feature_id] if item_id is None else items_id
        return self._multiprocess(lambda item: self.get_item(collection_id=collection_id, item_id=item), items_ids)

    def get_item_assets(self, item, assets_keys):
        """Get specified item assets reference link.

        Args:
            item (dict): an item dictionary.
            assets_keys (list): assets key list.

        Returns:
            [list[tuple]]: A list of tuples contaning assets id, title and reference link
        """
        #headers=self.headers
        # [(item_id, asset_title, asset_href)]
        return [(item.get('id'),
                item.get('assets').get(asset_key).get('title'),
                item.get('assets').get(asset_key).get('href')) for asset_key in assets_keys]

    def get_items_assets(self, items, assets_keys):
        """Get specified items assets reference links.

        Args:
            item (dict): an item dictionary.
            assets_keys (list): assets key list.

        Returns:
            [list[list[tuple]]]: A of list of tuples contaning assets id, title and reference link
        """
        # TODO FLATEN LIST
        #headers=self.headers
        return [self.get_item_assets(item=item, assets_keys=assets_keys) for item in items]

    def download(self, asset_ref):
        """Download source or label imagery asset.

        The `download` function create the label-item (tile X chip) and source-item (tile X chip x scene)
        parent directory `landcovernet/tile-id_chip-id/scene-id` if they do not exist.
        The `download` function download an asset given its reference link.


        Args:
            asset_ref (tuple): asset reference link tuple (path, href).
            root (str): root directory.
        """

        path, uri = asset_ref

        os.makedirs(path, exist_ok=True)

        download_uri = self._get_download_uri(uri)

        if download_uri is not None:
            parsed_uri = urlparse(download_uri)
            if parsed_uri.scheme in ['s3']:
                self._download_bucket(download_uri, path)
            elif parsed_uri.scheme in ['http', 'https']:
                self._download_http(download_uri, path)
            logger.info(f"Download asset {parsed_uri.path.split('/')[-1]} in path in directory {path}\n\
                {os.path.join(path,parsed_uri.path.split('/')[-1])}")

            self.assets_downloaded.append(asset_ref)
        else:
            logger.debug(f"The download url corresponding to the reference url\n{url}\n\
is returned as {type(download_uri)}")

    def downloads(self, assets_ref, leave):
        """Download multiple source or label imagery asset.

        The `downloads` function create the label-item (tile X chip) and source-item (tile X chip x scene)
        parent directories `landcovernet/tile-id_chip-id/scene-id` if they do not exist.
        The `downloads` function download multiple assets given their reference links.

        Args:
            assets_ref (list[tuples]): assets reference links list of tuples.
            root (str): root directory.
        """
        return self._multiprocess(lambda asset_ref: self.download(asset_ref=asset_ref), assets_ref, leave=leave)

    def get_item_source_assets(self, source_item_ref):
        """Get source-item assets hyperlinks links from a source-item.

        The `get_item_source_assets` function fetches a source-item assets (tile X chip x scene x band imagery)
        reference links for each the following 14 bands (B01, B02, B03, B04, B05, B06, B07, B08, B8A, B09, B11,
        B12, CLD, and SCL).

        Args:
            source_item (tuple): source-item destination path and reference link obtained from label-item
            relationship links.

        Returns:
            [type]: List of tuples source-items destination and reference links.
        """
        #TODO REPLACE BY get_items+get_items_assets GO FROM source item REF to ID
        #item_path: f'root/landcovernet/{item["id"]}/'
        #here there is a one-to-one mapping between item and label-item so item-path ~label-path
        label_item_path, hyperlink = source_item_ref
        response = self._get_uri(hyperlink, headers=self.headers)

        if response is not None:
            item = response.json()
            item_datetime = arrow.get(
                item.get('properties', {'datetime': '0001-01-01T00:00:00Z'}).get('datetime', '0001-01-01T00:00:00Z')
            ).format('YYYY_MM_DD')
            source_item_path = os.path.join(label_item_path, item_datetime)
            #TODO create path at downloads time
            #os.makedirs(source_item_path, exist_ok=True)
            source_item_assets_ref = [(source_item_path, asset['href']) for key, asset in item['assets'].items()]
            return source_item_assets_ref
        else:
            source_item_assets_ref = []
            logger.debug(f"No source item assets found for the {label_item_path}")
            return source_item_assets_ref

    def get_items_source_assets(self, source_items_ref):
        """Get source-item list assets hyperlinks links.

        The `get_item_source_assets` function fetches a source-item assets (tile X chip x scene x band imagery)
        reference links for each the following 14 bands (B01, B02, B03, B04, B05, B06, B07, B08, B8A, B09, B11,
        B12, CLD, and SCL).

        Args:
            source_item (tuple): source-item destination path and reference link obtained from label-item
            relationship links.

        Returns:
            [type]: List of list of tuples source-items destination and reference links.
        """
        return self._multiprocess(lambda item: self.get_item_source_assets(source_item_ref=item), source_items_ref)

    def get_item_all_assets(self, label_item):
        """Get label-item assset and related source-items assets reference links from a label-item.

        The `get_item_all_assets` function fetches the label-item asset (tile X chip imagery) and all
        the source-items assets (tile X chip X scene imagery X band) reference links for each feature
        belonging to the feature collections (ref_landcovernet_v1_source).

        Args:
            label_item (dict): One feature belonging to the API response labels feature-collection.

        Returns:
            list: List of tuples containing a label-item destination and reference links and with source-items
            destination and reference links.
        """
        label_list = self.get_item_assets(label_item, assets_keys=['labels'])  # OK
        label_item_id, _, item_label_hyperlink = label_list[0]  # OK
        item_path = f'landcovernet/{label_item_id}/'

        source_items_ref = [(item_path, item.get('href'))
                            for item in label_item.get('links')
                            if item.get('rel') == 'source']  # OK

        assets_ref = self.get_items_source_assets(source_items_ref=source_items_ref)  # OK
        assets_ref.append([(item_path, item_label_hyperlink)])
        # OK get_items_source_assets returns a list of list of tuples

        return assets_ref

    def get_items_all_assets(self,
                             uri,
                             classes=None,
                             max_items=None,
                             last_page=20,
                             limits=100,
                             items_downloaded=0,
                             collection_assets_ref=None):
        """Get item sets or feature collection assets reference links.

        The `get_items_all_assets` function recursively fetch items (tile X chip) sets source imagery and
        label reference links for each item belonging to the feature collection identified by the label
        collection_id `ref_landcovernet_v1_labels`and each item belonging to the feature related source
        collection_id `ref_landcovernet_v1_source`.

        The MLHub API response to each call is contained in a response document json file containing several
        attributes (context, feature, links, ...) with features sets of results of `size=limits`.
        The get_items function uses the `next` token contained in the current response document to
        retrieve the next set of results.

        Args:
            uri (str):
            classes (list, optional): Check if the item has one of the label classes of interest. Defaults to None.
            max_items (int, optional): Maximal total number of items to be returned. Defaults to None.
            limits (int, optional): Maximal number of items per response. Defaults to 100.
            items_downloaded (int, optional): Downloaded item counter. Defaults to 0.
            downloads_ref (list, optional): List of items destination and reference links tuples. Defaults to [].

        Returns:
            list: List of tuple containing labels and source collections destination and reference links
            for each item belonging to the item set.
        """
        #TODO Properly update crawler position
        if collection_assets_ref is None:
            collection_assets_ref = []

        collection_params = {'limit': limits}

        # - get_uri status to safely retrive response document
        if 'limits' in uri:
            response = self._get_uri(uri, headers=self.headers)
        else:
            response = self._get_uri(uri, headers=self.headers, params=collection_params)
        # safely unpack json document
        if response is not None:
            collection = response.json()
            for item in collection.get('features', []):
                logger.info(f"Getting label and source imagery for the item: {item.get('id', 'missing_id')}")
                assets_ref = self.get_item_source_and_label_assets(item)
                assets_ref_flat = list(chain(*assets_ref))
                collection_assets_ref.extend(assets_ref_flat)
                self.assets_fetched.extend(assets_ref_flat)
                items_downloaded += 1
                #results = collection_assets_ref.copy()

                #Stop retrieving items if max_items number is reach
                if max_items is not None and items_downloaded >= max_items:
                    return collection_assets_ref

            #Get the next page results, if available
            for link in collection.get('links', []):
                if link['rel'] == 'next' and link['href'] is not None:
                    self.get_items_source_and_label_assets(uri=link['href'], classes=classes,
                                                           max_items=max_items,
                                                           last_page=20, limits=limits,
                                                           items_downloaded=items_downloaded,
                                                           collection_assets_ref=collection_assets_ref)

        else:
            logger.info(f"No label or source imagery retrieved from url:\n{uri}")

            #Get the next page if results, if available
            next_page = int(re.findall(r'page=(.+?)&', uri)[0]) + 1
            next_uri = self.collection_items_uri + f"?&page={next_page}&limit={limits}"
            if next_page <= last_page:
                logger.info(f"Retrieving next page {next_page}:\n{next_uri}")
                self.get_items_source_and_label_assets(uri=next_uri, classes=classes, max_items=max_items,
                                                       last_page=20, limits=limits,
                                                       items_downloaded=items_downloaded,
                                                       collection_assets_ref=collection_assets_ref)

        return collection_assets_ref