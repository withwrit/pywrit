// Fixture: deprecated package-level generated client (the stripe-go
// pre-v87 shape): the package's last path segment is the resource.
// NOT flagged in slice 1, by design: the first family covers only the
// three-segment generated-client shape (<client>.<Resource>.<Method>).
// Telling charge.New(params) apart from a bare constructor like
// paymentsvc.New(cfg) needs import-aware detection, which is a later
// slice. This file pins that: the exact-match test asserts none of
// these lines is reported.
package main

import (
	charge "github.com/stripe/stripe-go/v87/charge"
	invoice "github.com/stripe/stripe-go/v87/invoice"
	acmeinvoice "example.com/acme/acme-payments/invoice"
)

func legacyCharge(params *stripe.ChargeParams) {
	charge.New(params)
	invoice.Update("in_123", nil)
	acmeinvoice.Delete("inv_9")
}
