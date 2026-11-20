// Fixture: GORM raw-SQL writes (slice 4). db.Raw / tx.Raw fire
// go-rawsql-write only when argument 0 is a string literal whose
// first keyword is a write verb (INSERT, UPDATE, DELETE, REPLACE,
// TRUNCATE, MERGE), case-insensitive. Stay silent: a read-first
// literal (SELECT), a variable SQL string, and a Raw call on a
// receiver that is not a db/tx handle. A leading WITH (CTE) is
// graded past since slice 5: see withcte.go for those cases.
// Lines tagged `expect:` must be flagged with that rule.
package main

func resetTemp(db *gorm.DB) {
	db.Raw(`TRUNCATE TABLE temp`).Scan(nil) // expect: go-rawsql-write
}

func backfillUsers(db *gorm.DB, q string, repo *Repo) {
	db.Raw("INSERT INTO audit_log (event) VALUES ('x')").Scan(nil) // expect: go-rawsql-write
	db.Raw("UPDATE users SET status = 'x'").Scan(nil)              // expect: go-rawsql-write
	db.Raw("DELETE FROM sessions WHERE id = 1").Scan(nil)          // expect: go-rawsql-write
	db.Raw("insert into audit_log (event) values ('x')").Scan(nil) // expect: go-rawsql-write

	q = "DELETE FROM sessions WHERE id = 1"
	db.Raw(q).Scan(nil)                     // variable: literal grade only, never fires
	db.Raw("SELECT id FROM users").Scan(nil) // read-first SQL: not a write
	repo.Raw("DELETE FROM sessions").Scan(nil) // Repo is not a db/tx handle: never fires
	gorm.Raw("DELETE FROM sessions").Scan(nil) // gorm package root: Raw is a helper, not a write
}

func auditTx(tx *gorm.DB) {
	tx.Raw("INSERT INTO audit_log (event) VALUES ('tx')").Scan(nil) // expect: go-rawsql-write
}
