"""Migre les échanges chat existants de epistememory vers chat_messages.

Crée un projet "Archive" et une conversation par date,
puis insère les messages Q/R séparément.
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pool import init_pool, get_conn


def migrate():
    init_pool()

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Fetch existing chat entries from epistememory
            cur.execute("""
                SELECT id, content, domain, tags, created_at
                FROM epistememory
                WHERE tags @> '{chat}'
                ORDER BY created_at ASC
            """)
            entries = cur.fetchall()

    if not entries:
        print("Aucun echange chat a migrer.")
        return

    print(f"Trouvé {len(entries)} echanges a migrer.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 2. Create "Archive" project
            cur.execute(
                "INSERT INTO chat_projects (name, description) VALUES (%s, %s) RETURNING id",
                ("Archive", "Conversations importées depuis epistememory"),
            )
            project_id = cur.fetchone()[0]
            print(f"Projet Archive créé: {project_id}")

            # 3. Group by date -> one conversation per day
            by_date = {}
            for entry_id, content, domain, tags, created_at in entries:
                day = created_at.date()
                if day not in by_date:
                    by_date[day] = []
                by_date[day].append((content, domain, tags, created_at))

            total_msgs = 0
            for day, day_entries in sorted(by_date.items()):
                # Create conversation for this day
                title = f"Chat du {day.strftime('%d/%m/%Y')}"
                cur.execute(
                    "INSERT INTO chat_conversations (title, project_id, created_at, updated_at) VALUES (%s, %s, %s, %s) RETURNING id",
                    (title, project_id, day_entries[0][3], day_entries[-1][3]),
                )
                conv_id = cur.fetchone()[0]

                for content, domain, tags, created_at in day_entries:
                    # Parse "Q: ... -> R: ..."
                    match = re.match(r'^Q:\s*(.*?)\s*->\s*R:\s*(.*)', content, re.DOTALL)
                    if match:
                        question = match.group(1).strip()
                        answer = match.group(2).strip()

                        # Insert user message
                        cur.execute(
                            "INSERT INTO chat_messages (conversation_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s)",
                            (conv_id, 'user', question, '{"migrated": true}', created_at),
                        )
                        # Insert etz response (1 second later)
                        cur.execute(
                            "INSERT INTO chat_messages (conversation_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s)",
                            (conv_id, 'etz', answer,
                             f'{{"migrated": true, "domain": "{domain}"}}',
                             created_at),
                        )
                        total_msgs += 2
                    else:
                        # Format non reconnu -> un seul message system
                        cur.execute(
                            "INSERT INTO chat_messages (conversation_id, role, content, metadata, created_at) VALUES (%s, %s, %s, %s, %s)",
                            (conv_id, 'system', content, '{"migrated": true}', created_at),
                        )
                        total_msgs += 1

                print(f"  {title}: {len(day_entries)} echanges -> conversation {conv_id}")

    print(f"Migration terminée: {len(by_date)} conversations, {total_msgs} messages.")


if __name__ == "__main__":
    migrate()
