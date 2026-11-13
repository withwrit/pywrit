// Fixture: request-pipeline clients that route calls through an
// internal Call / RawRequest method taking the HTTP method as
// argument 0 (the stripe-go Backend shape). Lines tagged `expect:`
// must be flagged with that rule.
package main

import (
	"context"
	"net/http"
)

// named so no segment ends in db/tx: the handle branch never matches.
type Gateway struct {
	B stripe.Backend
}

func overwriteAccount(c *Gateway, params *stripe.AccountParams, account *stripe.Account) {
	c.B.Call(http.MethodPost, "/v1/accounts", c.Key, params, account)    // expect: go-pipeline-write
	c.B.Call("DELETE", "/v1/accounts/acct_123", c.Key, nil, nil)         // expect: go-pipeline-write
	c.B.RawRequest(http.MethodPut, "/v1/accounts/acct_123", c.Key, nil, params) // expect: go-pipeline-write
}

func readsPastPipeline(c *Gateway, ctx context.Context, method string) {
	c.B.Call(http.MethodGet, "/v1/accounts", c.Key, nil, nil) // GET: read
	c.B.Call(http.MethodHead, "/v1/accounts", nil)            // HEAD: read
	c.B.Call(method, "/v1/accounts", nil)                     // variable method: not graded
	c.B.Call(ctx, http.MethodPost, "/v1/accounts", nil)       // context arg 0: not a method
}
