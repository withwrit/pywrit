// Fixture: slice-6 verb coverage, two set additions under the
// existing handle/receiver rules. GORM FirstOrCreate (reads first and
// creates the row when the lookup misses; that conditional create is a
// write) and CreateInBatches (batch insert) fire go-orm-write under
// the same handle rule as Create: the receiver chain must name a
// db/tx handle by convention (it is or ends in db/tx). http.PostForm
// (package-level) and client.PostForm (client handle) fire
// go-http-client-write under the same receiver rules as http.Post /
// client.Post. Attrs / Assign are modifiers, not writes alone, and
// stay off. POSTFORM is not an HTTP method string, so "POSTFORM" was
// not added to _GO_HTTP_WRITE_METHODS: a pipeline Call or NewRequest
// with "POSTFORM" as the method argument stays silent. Negatives
// below stay silent: a FirstOrCreate or CreateInBatches on a receiver
// segment that is not a db/tx handle (repo is not a handle name), a
// PostForm on a receiver with no client-shaped segment (relay), and
// reads past the new verbs (http.Get, client.Get).
// Lines tagged `expect:` must be flagged with that rule.
package main

import (
	"context"
	"net/http"
	"net/url"
)

var ctx = context.Background()

func upsertUser(db *gorm.DB, u *User) {
	db.FirstOrCreate(u)                  // expect: go-orm-write
	db.CreateInBatches([]User{*u}, 100)  // expect: go-orm-write
	db.WithContext(ctx).FirstOrCreate(u) // expect: go-orm-write
}

func submitForm(client *http.Client, url string, vals url.Values) {
	http.PostForm(url, vals)             // expect: go-http-client-write
	client.PostForm(url, vals)           // expect: go-http-client-write
}

// named so no segment ends in db/tx or client: the handle and client
// branches never match these receivers.
type Repo struct {
	repo  *gorm.DB
	relay *http.Client
}

func (r *Repo) negatives(u *User, url string, vals url.Values) {
	r.repo.FirstOrCreate(u)               // repo: not a db/tx handle
	r.repo.CreateInBatches([]User{*u}, 2) // repo: not a db/tx handle
	r.relay.PostForm(url, vals)           // relay: no client segment
	r.repo.Attrs("name", "ada")           // modifier, not a write alone
	r.repo.Assign("name", "ada")          // modifier, not a write alone
	http.Get(url)                         // GET read
	r.relay.Get(url)                      // GET read
	http.NewRequest("POSTFORM", url, nil) // not an HTTP write method
	r.relay.Call("POSTFORM", url, nil)    // not an HTTP write method
}
