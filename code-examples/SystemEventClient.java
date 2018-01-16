import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URL;
import java.security.cert.CertificateException;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;
import org.json.simple.JSONArray;  // json-simple-1.1.1.jar
import org.json.simple.JSONObject;  // json-simple-1.1.1.jar
import org.json.simple.parser.JSONParser;  // json-simple-1.1.1.jar


public class SystemEventClient {

    // Format to put data in table format based on how the UI presents the
    // information
    private static String alignFormat = "| %-4s | %-10s | %-20s | %-6s | %-7s | %-24s | %-24s | %-11s |%n";

    // Key to access the SP Leader
    private static String token = "bufFhFCg4f01z4iwLtvhtqhhHetVJlwyXdzlJeVl";

    /** Get annotation for given alert if it has one. */
    private static String get_annotation(JSONObject obj) throws Exception{
        // If the given alert has relationships
        JSONObject relationships = (JSONObject) obj.get("relationships");
        if(relationships != null) {
            JSONObject annotation_relationship = (
                (JSONObject) relationships.get("annotations"));

            // If there is a related annotation
            if(annotation_relationship != null) {
                String link = (String) ((JSONObject) (
                    annotation_relationship.get("links"))).get("related");

                // Query the related annotation's link
                JSONObject response = convert_to_json(request(link));
                JSONObject temp = (JSONObject) (
                    (JSONArray) response.get("data")).get(0);

                // Return the annotation
                return (String) ((JSONObject) temp.get("attributes")).get("text");
            }
        }

        // If there is no annotation return None
        return "None";
    }

    /** Parse JSON and print it according to how the UI presents it. */
    private static void print_ui(JSONObject json) throws Exception {
        // For each object in the array of results
        for (Object raw_json : (JSONArray) json.get("data")) {
            JSONObject obj = (JSONObject) raw_json;
            JSONObject attributes = (JSONObject) obj.get("attributes");

            // If the given alert is a System Event get information
            if((attributes.get("alert_class")).equals("system_event")) {
                String stop_time = "Ongoing";
                if(!(boolean) attributes.get("ongoing")) {
                    stop_time = (String) attributes.get("stop_time");
                }

                // Get the subobject for use getting the username and version
                JSONObject subobject = (
                    (JSONObject) attributes.get("subobject"));

                // Turn the given integer into a human-readable string for
                // importance
                String human_readable_importance[] = {"Low", "Medium", "High"};
                String string_importance = human_readable_importance[
                    (int) (long) attributes.get("importance")
                ];

                // Format results using alignFormat into table format
                System.out.format(alignFormat,
                    obj.get("id"),
                    string_importance,
                    "System Configuration Update",
                    subobject.get("username"),
                    subobject.get("version"),
                    attributes.get("start_time"),
                    stop_time,
                    get_annotation(obj));
            }
        }
    }

    /** Convert received content from connection to JSONObject. */
    private static JSONObject convert_to_json(HttpsURLConnection con) throws Exception {
        if (con == null || con.getResponseCode() != HttpsURLConnection.HTTP_OK) {
            return null;
        }

        // Get input from connection and parse it into json
        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(con.getInputStream()))) {
            final JSONParser parser = new JSONParser();
            return (JSONObject) parser.parse(br);

        } catch (IOException e) {
            e.printStackTrace();
        }
        return null;
    }

    /** Create Empty Trust Manager. */
    private static class DefaultTrustManager implements X509TrustManager {
        @Override
        public void checkClientTrusted(X509Certificate[] arg0, String arg1)
            throws CertificateException {}

        @Override
        public void checkServerTrusted(X509Certificate[] arg0, String arg1)
            throws CertificateException {}

        @Override
        public X509Certificate[] getAcceptedIssuers() {
            return null;
        }
    }

    /** Set up Https Connection with given SSL Certificate. */
    private static HttpsURLConnection request(String httpUrl) throws Exception {
        // Pass certificate to connection
        InputStream trustStream = new FileInputStream("./cacerts.jks");
        char[] password = null;
        KeyStore trustStore = KeyStore.getInstance(KeyStore.getDefaultType());
        trustStore.load(trustStream, password);

        // Set up TrustManager to pass to SSL Context
        TrustManagerFactory trustFactory = TrustManagerFactory.getInstance(
            TrustManagerFactory.getDefaultAlgorithm());
        trustFactory.init(trustStore);
        TrustManager[] trustManagers = { new DefaultTrustManager() };

        // Set up SSL Context
        SSLContext sslContext = SSLContext.getInstance("SSL");
        sslContext.init(null, trustManagers, new SecureRandom());
        SSLContext.setDefault(sslContext);

        // Open Connection to given url
        URL url;
        try {
            url = new URL(httpUrl);
            HttpsURLConnection con = (
                (HttpsURLConnection) url.openConnection());

            // Pass API Token and type to accept to the connection
            con.setRequestProperty("X-Arbux-APIToken", token);
            con.setRequestProperty("Accept", "application/json");

            // Return connection
            return con;

        } catch (MalformedURLException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return null;
    }

    /** Main: Trigger request for every page. */
    public static void main(String[] args) throws Exception {
        // Url to hit
        String httpUrl = "https://leader.example.com/api/sp/alerts/";

        // Print table headers
        System.out.format("+-------+------------+-----------------------------+--------+---------+---------------------------+---------------------------+-------------+%n");
        System.out.format("|  ID   | Importance |            Alert            |  User  | Version |        Start_Time         |        End_Time           | Annotations |%n");
        System.out.format("+-------+------------+-----------------------------+--------+---------+---------------------------+---------------------------+-------------+%n");

        // Loop through all pages of data
        HttpsURLConnection connection;
        JSONObject json;
        while (httpUrl !=  null) {
            // Make the query to the API with the given url
            connection = request(httpUrl);

            // Convert the response from the API into json
            json = convert_to_json(connection);

            // If there are no results break out of loop
            if (json == null) {
                break;
            }

            // Print the results formatted in table format
            print_ui(json);

            // Get `next` link if there is one in the pagination links (there
            // are more results)
            httpUrl = (String) ((JSONObject) json.get("links")).get("next");
        }

        // Print bottom of table
        System.out.format("+-------+------------+-----------------------------+--------+---------+---------------------------+---------------------------+-------------+%n");
    }
}

