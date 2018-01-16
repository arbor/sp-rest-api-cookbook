#include <curl/curl.h>
#include <jansson.h>
#include <stdio.h>
#include <string.h>

/*
 * Retrieve information on managed objects using the SP REST API and
 * print a table of some of the fields
 *
 * This program requires two libraries:
 *  - jansson from http://www.digip.org/jansson/
 *  - libcurl from https://curl.haxx.se/
 *  - compile about like:
 *    gcc -I ... -L ... mo-listing.c -l jansson -l curl -o molisting
 *    replacing "..." with the include and library paths for your
 *    system
 */

#define REPORT_WIDTH 92
#define IS_CHILD_STRLEN 4

struct curlMemoryStruct {
  char *memory;
  size_t size;
};

static json_t *load_json(char *);
static void print_mo_list(json_t *);
static void do_curl(struct curlMemoryStruct *,
		    const char *,
		    char *);
static size_t storeCurlData(void *, size_t,
			    size_t, void *);
static void extract_and_print(json_t *);
static void format_mo(json_t *, char *,
		      json_t *, json_t *);

/**
 * take a Jansson JSON data structure and print it out
 *
 * @param[in] json_t *root; the root of the Jansson data
 *
 */
static void print_mo_list(json_t *root) {
  json_t *data;
  size_t array_index;
  json_t *array_value;

  if (root == NULL) {
    fprintf(stderr, "[ERROR] No JSON data processed.\n");
    return;
  }
  data = json_object_get(root, "data");
  if (data == NULL) {
    fprintf(stderr, "[ERROR] No 'data' element in JSON from API\n");
    return;
  }

  if (json_typeof(data) == JSON_OBJECT) {
    extract_and_print(data);
  } else if (json_typeof(data) == JSON_ARRAY) {
    json_array_foreach(data, array_index, array_value) {
      extract_and_print(array_value);
    }
  }
  return;
}

/**
 * Pick out the parts of the managed object JSON structure that we
 * want and send them to the printing function.
 *
 * @param[in] json_t *mo; a JSON object from the SP REST API
 *                        representing a SP managed object
 *
 */
static void extract_and_print(json_t *mo) {
  json_t *name, *parent_name, *match_type, *match_value, *attributes;
  char is_child[10];

  attributes = json_object_get(mo, "attributes");
  if (attributes != NULL && json_typeof(attributes) == JSON_OBJECT) {
    name = json_object_get(attributes, "name");
    parent_name = json_object_get(attributes, "parent_name");
    if (parent_name != NULL) {
      strlcpy(is_child, "Yes", IS_CHILD_STRLEN);
    } else {
      strlcpy(is_child, "", IS_CHILD_STRLEN);
    }
    match_type = json_object_get(attributes, "match_type");
    match_value = json_object_get(attributes, "match");

    format_mo(name, is_child, match_type, match_value);
  }
}

/**
 * Print the name, child status, match type, and match value of a
 * managed object in a formatted way.
 *
 * @param[in] json_t *name; a Jansson json_t with the name of the MO
 * @param[in] char *is_chile; a string that is "Child" or ""
 * representing whether or not the MO is a child MO
 * @param[in] json_t *match_type; a Jansson json_t with the match
 * type setting for the MO
 * @param[in] json_t *match_value; a Jansson json_t with the match
 * value for the MO
 */
static void format_mo(json_t *name, char *is_child, json_t *match_type,
               json_t *match_value) {
  printf("| %25.25s | ", json_string_value(name));
  printf("%6.6s | ", is_child);
  printf("%15.15s | ", json_string_value(match_type));
  printf("%33.33s | ", json_string_value(match_value));
  printf("\n");
}

/**
 * The callback function for storing data retrieved via
 * curl_easy_perform()
 *
 * this is pretty much taken exactly from
 * https://curl.haxx.se/libcurl/c/getinmemory.html, as suggested by
 * the man pages for these two `CURLOPT_` parameters
 *
 * @param[in] void *content; a pointer to the cURL data structure
 * @param[in] size_t size; size information of the retrieved data
 * @param[in] size_t nmemb; size information of the retrieved data
 * @param[in] void *userp; what the cURL docs say to have
 * @param[out] size_t realsize; the size of the data successfully
 * stored
 */
static size_t storeCurlData(void *contents, size_t size, size_t nmemb, void *userp) {
  size_t realsize = size * nmemb;
  struct curlMemoryStruct *mem = (struct curlMemoryStruct *)userp;

  /* Make space in our char struct element for the new contents. */
  mem->memory = realloc(mem->memory, mem->size + realsize + 1);
  if (mem->memory == NULL) {
    fprintf(stderr, "[ERROR] Not enough memory to store data "
	    "from cURL (realloc returned NULL)\n");
    return 0;
  }

  /*
   *  Put the data in `contents` into our char struct element to save
   * it for later, and update the size of the overall struct
   */
  memcpy(&(mem->memory[mem->size]), contents, realsize);
  mem->size += realsize;
  mem->memory[mem->size] = 0;

  return realsize;
}

/**
 * Make the HTTP request to the API endpoint.
 *
 * @param[in] curlMemoryStruct *chunk; the cURL memory for the
 * results
 * @param[in] const char *url; the URL to retrieve
 * @param[in] char *api_key; the API key string, including the
 * "X-Arbux-Token" component
 *
 */
void do_curl(struct curlMemoryStruct *chunk, const char *url, char *api_key) {
  struct curl_slist *list = NULL;
  CURLcode results;
  CURL *curl;

  curl = curl_easy_init();

  if (curl) {
    /* Set the URL we want to retrieve. */
    curl_easy_setopt(curl, CURLOPT_URL, url);

    /* Add to the list that we'll use as headers. */
    list = curl_slist_append(list, api_key);

    /* Set the headers to be the things in the list we made. */
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, list);

    /* Point to an Arbor certificate file */
    curl_easy_setopt(curl, CURLOPT_CAINFO,
                     "./certfile");

    /*
     * Set the callback function and the data structure for the data,
     * this is pretty much taken exactly from
     * https://curl.haxx.se/libcurl/c/getinmemory.html, as suggested
     * by the man pages for these two `CURLOPT_` parameters
     */
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, storeCurlData);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)chunk);

    /* Do the HTTP GET. */
    results = curl_easy_perform(curl);

    /* Clean everything up. */
    curl_slist_free_all(list);
    curl_easy_cleanup(curl);

    /* Print the curl return code integer if there is an error. */
    if (results != CURLE_OK) {
      fprintf(stderr,
	      "\n[ERROR] cURL return status: `%s' (%d)\n",
	      curl_easy_strerror(results),
	      results);
    }
  }

  return;
}

int main() {
  json_t *rootOfJsonTree, *links;
  json_error_t error;
  const char *url =
      "https://leader.example.com/api/sp/managed_objects/?perPage=15";
  char *apikey = "X-Arbux-APIToken:eFvokphdyGHA_M4oLlLtfDnlIf9bpjFnn0mWlDqw";
  struct curlMemoryStruct dataFromCurl;
  json_t *meta, *api_version, *sp_version;

  printf("| %25.25s | ", " Name ");
  printf("%6.6s | ", "Child?");
  printf("%15.15s | ", " Match Type ");
  printf("%33.33s | ", " Match Values ");
  printf("\n");
  for (int i = 0; i < REPORT_WIDTH; i++) {
    printf("-");
  }
  printf("\n");

  while (url != NULL) {

    /*
     * The memory element will be increased as the data from curl is
     * retrieved, so 1 byte is sufficient for now.
     */
    dataFromCurl.memory = malloc(1);
    /* We don't have any data at this point, so the size is 0. */
    dataFromCurl.size = 0;

    do_curl(&dataFromCurl, url, apikey);

    /*
     * Take the JSON returned from curl and parse it into a Jansson
     * data structure.
     */
    if (dataFromCurl.size < 1) {
      fprintf(stderr, "[ERROR] No data was returned from cURL, exiting.\n");
      exit(1);
    }
    rootOfJsonTree = json_loads(dataFromCurl.memory, 0, &error);
    if (rootOfJsonTree == NULL) {
      fprintf(stderr, "[ERROR] JSON decode error message: %s\n",
	      error.text);
      exit(1);
    }
    /*
     * Do something with the results; in this case, just print them
     * out; storing them for later processing is also a good idea.
     */
    print_mo_list(rootOfJsonTree);
    /*
     * Check for more data to get by looking for the 'next' key in the
     * 'links' section.
     */
    links = json_object_get(rootOfJsonTree, "links");
    if (links == NULL) {
      fprintf(stderr, "[ERROR] The 'links' element in the "
	      "returned JSON is null\n");
      url = NULL;
    } else {
      url = json_string_value(json_object_get(links, "next"));
    }
  }
  /*
   * Print a table footer and the version of the SP API that was
   * used.
   */

  meta = json_object_get(rootOfJsonTree, "meta");
  api_version = json_object_get(meta, "api_version");
  sp_version = json_object_get(meta, "sp_version");
  for (int i = 0; i < REPORT_WIDTH; i++) {
    printf("-");
  }
  printf("\n");
  printf("%80s SP%s/APIv%s\n",
         "SP REST API version:", json_string_value(sp_version),
         json_string_value(api_version));
  /*
   * Free (or at least decrement the references to) the json data
   * structure.
   */
  json_decref(rootOfJsonTree);
  exit(0);
}
