// Fixture: package-level generated clients (the stripe-go pre-v87
// shape): the package's last import-path segment is the resource and
// the write method hangs off the package itself. Flagged since
// slice 3 via the import-aware `go-pkgclient-write` rule: a
// two-segment <pkg>.<New|Update|Delete|Create> call fires only when
// <pkg> is imported in this file AND the import path's last segment is
// resource-shaped (not structy like params/config, not
// service/client/library-shaped like svc/client/internal). Lines
// tagged `expect:` must be flagged with that rule; the untagged calls
// below must NOT be reported: a bare local constructor with no matching
// import, a constructor on an imported service-shaped package, and a
// .New on an imported structy package.
package main

import (
	charge "github.com/stripe/stripe-go/v87/charge"
	invoice "github.com/stripe/stripe-go/v87/invoice"
	acmeinvoice "example.com/acme/acme-payments/invoice"
	paymentsvc "example.com/acme/paymentsvc"
	"example.com/acme/config"
	"example.com/acme/internal"
)

func legacyCharge(params *stripe.ChargeParams) {
	charge.New(params)             // expect: go-pkgclient-write
	invoice.Update("in_123", nil)  // expect: go-pkgclient-write
	acmeinvoice.Delete("inv_9")    // expect: go-pkgclient-write
}

func negatives(cfg *Config, svc *Service) {
	paymentsvc.New(cfg) // imported service-shaped package: constructor, not a write
	config.New()        // imported structy package: no resource
	internal.Create()   // imported layer-shaped package: no resource
	svc.New(cfg)        // local variable, no import: never a package call
}
