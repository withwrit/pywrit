import { Pool } from "pg";

const pool = new Pool();

export async function placeOrder(orderId: string): Promise<void> {
  await pool.query("UPDATE orders SET status = $1 WHERE id = $2", ["refunded", orderId]);
}

// trigger rescan after PYTHONPATH fix
export async function noOp(): Promise<void> {}

# final re-smoke: ts snippet -> money risk class
