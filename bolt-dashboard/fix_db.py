import sqlite3

conn = sqlite3.connect("/var/lib/smarter/metrics.db")
cur = conn.cursor()

# Find bad rows
bad_statuses = ["Café Americano", "Completo Italiano", "Hamburguesa Clásica", 
                "Pizza Grande", "Sushi Roll", "Doble Hamburguesa completa con delivery"]

cur.execute("SELECT COUNT(*) FROM events WHERE status IN ({})".format(
    ",".join(["?"]*len(bad_statuses))), bad_statuses)
print("Bad rows found:", cur.fetchone()[0])

# Fix: move product name to producto column, set status to VALID
cur.execute("""
    UPDATE events 
    SET producto = status, status = 'VALID'
    WHERE status IN ({})
""".format(",".join(["?"]*len(bad_statuses))), bad_statuses)
print("Fixed:", cur.rowcount)
conn.commit()

# Verify
cur.execute("SELECT status, COUNT(*) FROM events GROUP BY status ORDER BY status")
print("\nStatus distribution after fix:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\nTotal events:", cur.execute("SELECT COUNT(*) FROM events").fetchone()[0])
conn.close()
print("\n✅ Database cleaned successfully")
