// Fixture: HTTP client writes. Lines tagged `expect:` must be flagged
// with that rule.
package main

import (
	"bytes"
	"net/http"
)

var defaultClient = &http.Client{}

func submitOrder(client *http.Client, url string, body []byte) {
	client.Post(url, "application/json", bytes.NewReader(body))        // expect: go-http-client-write
	client.Put(url, "application/json", bytes.NewReader(body))         // expect: go-http-client-write
	client.Patch(url, "application/json", bytes.NewReader(body))       // expect: go-http-client-write
	client.Delete(url)                                                 // expect: go-http-client-write
	http.Post(url, "application/json", bytes.NewReader(body))          // expect: go-http-client-write
	http.Put(url, "application/json", bytes.NewReader(body))           // expect: go-http-client-write
	http.NewRequest("POST", url, nil)                                  // expect: go-http-request-write
	http.NewRequest("PUT", url, nil)                                   // expect: go-http-request-write
	http.NewRequestWithContext(ctx, http.MethodPatch, url, nil)        // expect: go-http-request-write
	http.NewRequest(http.MethodDelete, url, nil)                       // expect: go-http-request-write
	defaultClient.Post(url, "text/plain", nil)                         // expect: go-http-client-write
}
