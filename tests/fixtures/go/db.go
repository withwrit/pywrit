// Fixture: database/sql and GORM-shaped writes. Lines tagged `expect:`
// must be flagged with that rule.
package main

import (
	"context"
	"database/sql"
)

var ctx = context.Background()

func deleteOrder(db *sql.DB, id string) {
	db.Exec("DELETE FROM orders WHERE id = $1", id)                    // expect: go-db-write
	db.ExecContext(ctx, "UPDATE orders SET state = $1", "cancelled")   // expect: go-db-write
}

type Store struct {
	db *sql.DB
}

func (s *Store) purgeSession(tx *sql.Tx, id string) {
	tx.Exec("DELETE FROM sessions WHERE id = $1", id) // expect: go-db-write
	s.db.Exec("UPDATE sessions SET live = false")     // expect: go-db-write
}

func createUser(gormDB *gorm.DB, u *User, id int64) {
	gormDB.Create(u)                                   // expect: go-orm-write
	gormDB.Save(u)                                     // expect: go-orm-write
	gormDB.Model(u).Update("name", "ada")              // expect: go-orm-write
	gormDB.Model(u).Updates(User{Name: "ada"})         // expect: go-orm-write
	gormDB.Delete(u, id)                               // expect: go-orm-write
	gormDB.WithContext(ctx).Create(u)                  // expect: go-orm-write
}
