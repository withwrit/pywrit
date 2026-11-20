// Fixture: GORM raw-SQL writes behind a leading WITH (slice 5).
// db.Raw / tx.Raw fire go-rawsql-write when argument 0 is a string
// literal whose CTE list parses and whose main statement verb is a
// write verb (INSERT, UPDATE, DELETE, REPLACE, TRUNCATE, MERGE),
// case-insensitive. The walk is a real parse: a write verb inside a
// CTE query never decides the grade, the main statement verb does.
// Stay silent: a WITH ... SELECT main statement (read), a WITH CTE
// write on a non-handle receiver, and a malformed WITH (off-shape
// forms like an unclosed quoted name or a CTE list with no main
// statement never reach a write verb). Quoted CTE names appear via
// backtick raw strings only: the raw literal value keeps backslash
// escapes, so an interpreted literal can only embed double quotes,
// which the SQL name walk does not de-escape. The variable-SQL case
// is covered in rawsql.go (a non-literal argument never fires).
// Lines tagged `expect:` must be flagged with that rule.
package main

func purgeExpired(db *gorm.DB) {
	db.Raw("WITH old AS (SELECT id FROM sessions WHERE expired = true) DELETE FROM sessions WHERE id IN (SELECT id FROM old)").Scan(nil) // expect: go-rawsql-write
	db.Raw("WITH moved AS (SELECT * FROM temp) INSERT INTO archive SELECT * FROM moved").Scan(nil)                                     // expect: go-rawsql-write
	db.Raw("WITH u AS (SELECT id FROM users WHERE banned = true) UPDATE users SET status = 'x' WHERE id IN (SELECT id FROM u)").Scan(nil) // expect: go-rawsql-write
	db.Raw("with t as (select * from tmp) insert into archive select * from t").Scan(nil)                                              // expect: go-rawsql-write
	db.Raw(`WITH q AS (SELECT * FROM queue WHERE done = false) DELETE FROM queue WHERE id IN (SELECT id FROM q)`).Scan(nil)            // expect: go-rawsql-write
	db.Raw("WITH recent AS (SELECT id FROM audit_log LIMIT 10) SELECT * FROM recent").Scan(nil)       // WITH ... SELECT: a read, never fires
	db.Raw("WITH t AS (SELECT * FROM a)").Scan(nil)                                                   // no main verb: malformed
	db.Raw("WITH `unterminated AS (SELECT * FROM a) DELETE FROM b").Scan(nil)                         // malformed: unclosed quoted name
}

func archiveOrders(db *gorm.DB) {
	db.Raw("WITH a AS (SELECT id FROM orders WHERE done = true), b AS (SELECT * FROM archive WHERE y = (SELECT MAX(y) FROM archive_years)) DELETE FROM orders WHERE id IN (SELECT id FROM a)").Scan(nil) // expect: go-rawsql-write
	db.Raw("WITH RECURSIVE r AS (SELECT n FROM nums) SELECT n FROM r").Scan(nil)         // RECURSIVE walk, still a read
	db.Raw("WITH t (id, n) AS (SELECT id, n FROM a) SELECT n FROM t").Scan(nil)          // column list parse, still a read
	db.Raw("WITH t AS MATERIALIZED (SELECT * FROM a) SELECT * FROM t").Scan(nil)         // MATERIALIZED read
	db.Raw("WITH t AS NOT MATERIALIZED (SELECT * FROM a) SELECT * FROM t").Scan(nil)     // NOT MATERIALIZED read
	db.Raw("WITH ids AS (DELETE FROM t RETURNING id) SELECT * FROM ids").Scan(nil)       // verb inside the CTE does not decide: main SELECT is a read
}

func queueAuditTx(sqlStore *Store) {
	sqlStore.Raw("WITH t AS (SELECT id FROM q) DELETE FROM q WHERE id IN (SELECT id FROM t)").Scan(nil) // Store is not a db/tx handle: never fires
}
