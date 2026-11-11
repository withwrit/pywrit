// Fixture: generated-client resource methods (the stripe-go shape).
// Lines tagged `expect:` must be flagged with that rule.
package main

func chargeCard(sc *client.API, params *stripe.ChargeParams) {
	sc.Charges.New(params)                          // expect: go-sdk-write
	sc.Customers.Update("cus_123", nil)             // expect: go-sdk-write
	sc.Customers.Delete("cus_123")                  // expect: go-sdk-write
	sc.Invoices.Create(nil)                         // expect: go-sdk-write
}

func nested(client *Client) {
	client.V1.Charges.New(nil)                      // expect: go-sdk-write
}
