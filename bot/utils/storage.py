import asyncio
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "bot.db"
_db_lock = asyncio.Lock()


async def _ensure_column(db: aiosqlite.Connection, table: str, column: str, ddl: str):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        cols = [row[1] for row in await cursor.fetchall()]
    if column not in cols:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS guild_settings ("
            "guild_id INTEGER PRIMARY KEY, "
            "welcome_channel_id INTEGER, "
            "ticket_panel_channel_id INTEGER"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS ticket_categories ("
            "guild_id INTEGER, "
            "label TEXT, "
            "category_id INTEGER, "
            "PRIMARY KEY (guild_id, label)"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS greeted_users ("
            "guild_id INTEGER, "
            "user_id INTEGER, "
            "PRIMARY KEY (guild_id, user_id)"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS giveaways ("
            "message_id INTEGER PRIMARY KEY, "
            "guild_id INTEGER, "
            "channel_id INTEGER, "
            "prize TEXT, "
            "winners INTEGER, "
            "end_at INTEGER, "
            "host_id INTEGER, "
            "ended INTEGER DEFAULT 0"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS invites ("
            "guild_id INTEGER, "
            "inviter_id INTEGER, "
            "invited_id INTEGER, "
            "invite_code TEXT, "
            "joined_at INTEGER, "
            "left_at INTEGER, "
            "PRIMARY KEY (guild_id, invited_id)"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS warnings ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "guild_id INTEGER, "
            "user_id INTEGER, "
            "moderator_id INTEGER, "
            "reason TEXT, "
            "created_at INTEGER"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS reviews ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "guild_id INTEGER, "
            "user_id INTEGER, "
            "stars INTEGER, "
            "text TEXT, "
            "created_at INTEGER"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS economy ("
            "guild_id INTEGER, "
            "user_id INTEGER, "
            "coins INTEGER, "
            "streak INTEGER, "
            "last_claim INTEGER, "
            "PRIMARY KEY (guild_id, user_id)"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS ai_knowledge ("
            "guild_id INTEGER, "
            "question TEXT, "
            "answer TEXT, "
            "PRIMARY KEY (guild_id, question)"
            ")"
        )

        await _ensure_column(db, "guild_settings", "suggestion_channel_id", "suggestion_channel_id INTEGER")
        await _ensure_column(db, "guild_settings", "rules_channel_id", "rules_channel_id INTEGER")
        await _ensure_column(db, "guild_settings", "welcome_message", "welcome_message TEXT")
        await _ensure_column(db, "guild_settings", "ticket_panel_message_id", "ticket_panel_message_id INTEGER")
        await _ensure_column(db, "guild_settings", "command_channel_id", "command_channel_id INTEGER")
        await _ensure_column(db, "guild_settings", "report_channel_id", "report_channel_id INTEGER")
        await _ensure_column(db, "guild_settings", "review_channel_id", "review_channel_id INTEGER")

        await db.commit()


async def get_welcome_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT welcome_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_welcome_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, welcome_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET welcome_channel_id = excluded.welcome_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_rules_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT rules_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_rules_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, rules_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET rules_channel_id = excluded.rules_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_welcome_message(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT welcome_message FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_welcome_message(guild_id: int, message: str):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, welcome_message) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET welcome_message = excluded.welcome_message",
                (guild_id, message),
            )
            await db.commit()


async def get_suggestion_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT suggestion_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_suggestion_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, suggestion_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET suggestion_channel_id = excluded.suggestion_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_command_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT command_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_command_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, command_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET command_channel_id = excluded.command_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_report_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT report_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_report_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, report_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET report_channel_id = excluded.report_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_review_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT review_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_review_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, review_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET review_channel_id = excluded.review_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_ticket_panel_channel_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ticket_panel_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_ticket_panel_channel_id(guild_id: int, channel_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, ticket_panel_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET ticket_panel_channel_id = excluded.ticket_panel_channel_id",
                (guild_id, channel_id),
            )
            await db.commit()


async def get_ticket_panel_message_id(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT ticket_panel_message_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def set_ticket_panel_message_id(guild_id: int, message_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO guild_settings (guild_id, ticket_panel_message_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET ticket_panel_message_id = excluded.ticket_panel_message_id",
                (guild_id, message_id),
            )
            await db.commit()


async def set_ticket_categories(guild_id: int, categories: list[tuple[str, int]]):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM ticket_categories WHERE guild_id = ?", (guild_id,))
            await db.executemany(
                "INSERT INTO ticket_categories (guild_id, label, category_id) VALUES (?, ?, ?)",
                [(guild_id, label, category_id) for label, category_id in categories],
            )
            await db.commit()


async def get_ticket_categories(guild_id: int) -> list[tuple[str, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT label, category_id FROM ticket_categories WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [(r[0], r[1]) for r in rows]


async def was_greeted(guild_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM greeted_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def mark_greeted(guild_id: int, user_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO greeted_users (guild_id, user_id) VALUES (?, ?)",
                (guild_id, user_id),
            )
            await db.commit()


async def add_giveaway(guild_id: int, channel_id: int, message_id: int, prize: str, winners: int, end_at: int, host_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO giveaways (message_id, guild_id, channel_id, prize, winners, end_at, host_id, ended)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (message_id, guild_id, channel_id, prize, winners, end_at, host_id),
            )
            await db.commit()


async def get_giveaway(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id, guild_id, channel_id, prize, winners, end_at, host_id, ended FROM giveaways WHERE message_id = ?",
            (message_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "message_id": row[0],
                "guild_id": row[1],
                "channel_id": row[2],
                "prize": row[3],
                "winners": row[4],
                "end_at": row[5],
                "host_id": row[6],
                "ended": row[7],
            }


async def mark_giveaway_ended(message_id: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE giveaways SET ended = 1 WHERE message_id = ?",
                (message_id,),
            )
            await db.commit()


async def get_active_giveaways():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id, guild_id, channel_id, prize, winners, end_at, host_id FROM giveaways WHERE ended = 0",
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                results.append(
                    {
                        "message_id": r[0],
                        "guild_id": r[1],
                        "channel_id": r[2],
                        "prize": r[3],
                        "winners": r[4],
                        "end_at": r[5],
                        "host_id": r[6],
                    }
                )
            return results


async def add_invite_record(guild_id: int, inviter_id: int, invited_id: int, invite_code: str, joined_at: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO invites (guild_id, inviter_id, invited_id, invite_code, joined_at, left_at) "
                "VALUES (?, ?, ?, ?, ?, NULL) "
                "ON CONFLICT(guild_id, invited_id) DO UPDATE SET "
                "inviter_id = excluded.inviter_id, "
                "invite_code = excluded.invite_code, "
                "joined_at = excluded.joined_at, "
                "left_at = NULL",
                (guild_id, inviter_id, invited_id, invite_code, joined_at),
            )
            await db.commit()


async def mark_invite_left(guild_id: int, invited_id: int, left_at: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE invites SET left_at = ? WHERE guild_id = ? AND invited_id = ?",
                (left_at, guild_id, invited_id),
            )
            await db.commit()


async def get_invite_stats(guild_id: int, inviter_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), "
            "SUM(CASE WHEN left_at IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM invites WHERE guild_id = ? AND inviter_id = ?",
            (guild_id, inviter_id),
        ) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0
            left = row[1] if row and row[1] is not None else 0
            return total, left


async def get_invited_list(guild_id: int, inviter_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT invited_id, joined_at, left_at, invite_code "
            "FROM invites WHERE guild_id = ? AND inviter_id = ? "
            "ORDER BY joined_at DESC LIMIT ?",
            (guild_id, inviter_id, limit),
        ) as cursor:
            return await cursor.fetchall()


async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str, created_at: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (guild_id, user_id, moderator_id, reason, created_at),
            )
            await db.commit()


async def get_warning_count(guild_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0] or 0)


async def add_review(guild_id: int, user_id: int, stars: int, text: str, created_at: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO reviews (guild_id, user_id, stars, text, created_at) VALUES (?, ?, ?, ?, ?)",
                (guild_id, user_id, stars, text, created_at),
            )
            await db.commit()


async def get_review_leaderboard(guild_id: int, since_ts: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, AVG(stars) as avg_stars, COUNT(*) as total "
            "FROM reviews WHERE guild_id = ? AND created_at >= ? "
            "GROUP BY user_id "
            "ORDER BY avg_stars DESC, total DESC "
            "LIMIT ?",
            (guild_id, since_ts, limit),
        ) as cursor:
            return await cursor.fetchall()


async def get_economy(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT coins, streak, last_claim FROM economy WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"coins": 0, "streak": 0, "last_claim": 0}
            return {"coins": row[0] or 0, "streak": row[1] or 0, "last_claim": row[2] or 0}


async def set_economy(guild_id: int, user_id: int, coins: int, streak: int, last_claim: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO economy (guild_id, user_id, coins, streak, last_claim) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                "coins = excluded.coins, streak = excluded.streak, last_claim = excluded.last_claim",
                (guild_id, user_id, coins, streak, last_claim),
            )
            await db.commit()


async def add_coins(guild_id: int, user_id: int, amount: int):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO economy (guild_id, user_id, coins, streak, last_claim) "
                "VALUES (?, ?, ?, 0, 0) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET coins = coins + ?",
                (guild_id, user_id, amount, amount),
            )
            await db.commit()


async def get_balance(guild_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT coins FROM economy WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0] or 0) if row else 0


async def upsert_knowledge(guild_id: int, question: str, answer: str):
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO ai_knowledge (guild_id, question, answer) VALUES (?, ?, ?) "
                "ON CONFLICT(guild_id, question) DO UPDATE SET answer = excluded.answer",
                (guild_id, question, answer),
            )
            await db.commit()


async def get_knowledge(guild_id: int, question: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT answer FROM ai_knowledge WHERE guild_id = ? AND question = ?",
            (guild_id, question),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def delete_knowledge(guild_id: int, question: str) -> bool:
    async with _db_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM ai_knowledge WHERE guild_id = ? AND question = ?",
                (guild_id, question),
            )
            await db.commit()
            return cursor.rowcount > 0


async def list_knowledge(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT question, answer FROM ai_knowledge WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            return await cursor.fetchall()
