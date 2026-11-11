// Fixture (negative): reads and look-alikes. Nothing here may be
// flagged.
package main

import (
	"database/sql"
	"net/http"
)

func loadOrders(db *sql.DB, client *http.Client, url string, method string) {
	db.Query("SELECT * FROM orders")                 // read: not Exec
	db.QueryRow("SELECT id FROM orders LIMIT 1")     // read
	db.QueryContext(ctx, "SELECT 1")                 // read
	http.Get(url)                                    // GET: read
	http.Head(url)                                   // HEAD: read
	client.Get(url)                                  // GET: read
	http.NewRequest("GET", url, nil)                 // GET: read
	http.NewRequest("HEAD", url, nil)                // HEAD: read
	http.NewRequest(method, url, nil)                // variable method: not graded
	http.NewRequestWithContext(ctx, http.MethodGet, url, nil)  // GET: read
	svc := paymentsvc.New(cfg)                       // bare constructor
	n := widget.New()                                // bare constructor
	c := cache.New(cfg).WithTTL(t)                   // constructor chain
	fmt.Println("hi")                                // not a write
	cache.Delete(k)                                  // map/cache, not a db handle
	s.Info.Update()                                  // not a db handle
	rows.Scan(&id)                                   // read
	gorm.Raw("DELETE FROM t").Scan(&dst)             // raw-sql path: later slice
}
