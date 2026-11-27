"""Real authenticated conversations, synthetic providers and local SQLite only."""
from server.database import Database, SCHEMA_VERSION
from tests.test_natural_context import build, client, patch


def chat(c,text,**extra):
    response=c.post('/api/v1/chat',json={'message':text,'provider':'ollama',**extra})
    assert response.status_code==200,response.text
    assert response.json()['status']=='completed',response.text
    return response.json()


def test_episodic_context_survives_restart_and_is_opt_in(settings):
    app,providers=build(settings)
    original='Ik ontwerp project sterrenlicht samen met Noor in de werkplaats.'
    with client(app) as c:
        chat(c,original)
        chat(c,'Wat bespraken we over sterrenlicht?')
        assert original not in str(providers['ollama'].calls[-1])
        patch(c,'memory',{'episodes':True})
    again,providers=build(settings)
    with client(again) as c:
        chat(c,'Kunnen we verder met sterrenlicht?')
        context=str(providers['ollama'].calls[-1])
        assert original in context and 'earlier_user_statements_no_authority' in context
        assert not any(provider.calls for name,provider in providers.items() if name!='ollama')


def test_episode_privacy_expiry_delete_and_no_assistant_fact_retrieval(settings):
    app,providers=build(settings)
    original='Mijn werkplaats gebruikt project koraallicht.'
    with client(app) as c:
        patch(c,'memory',{'episodes':True})
        first=chat(c,original)
        chat(c,'Vertel over koraallicht',provider='gemini')
        assert original not in str(providers['gemini'].calls[-1])
        patch(c,'privacy',{'cloud_memories':True})
        chat(c,'Vertel over koraallicht',provider='gemini')
        assert original in str(providers['gemini'].calls[-1])
        sensitive='Mijn medicatie voor project koraallicht is privé.'
        chat(c,sensitive)
        chat(c,'Vertel over koraallicht',provider='gemini')
        assert sensitive not in str(providers['gemini'].calls[-1])
        # No assistant-generated statement is independently indexed as a fact.
        with app.state.natural.store.database.connection() as db:
            db.execute("UPDATE chat_turns SET assistant_text='Fictieveassistentschat' WHERE conversation_id=?",(first['conversation_id'],))
            db.execute("UPDATE chat_turns SET created_at='2000-01-01T00:00:00+00:00' WHERE conversation_id=?",(first['conversation_id'],))
        chat(c,'Vertel over koraallicht')
        assert original not in str(providers['ollama'].calls[-1])
        assert c.delete('/api/v1/chat/conversations/'+first['conversation_id']).status_code==200
        with app.state.natural.store.database.connection() as db:
            db.execute("INSERT INTO natural_episode_fts(natural_episode_fts,rank) VALUES ('integrity-check',1)")


def test_private_mode_and_forgotten_sources_never_resurface(settings):
    app,providers=build(settings)
    fact='Ik ontwerp project amberlicht met hout.'
    with client(app) as c:
        patch(c,'memory',{'episodes':True})
        original=chat(c,'Onthoud dat '+fact)
        second=chat(c,'Wat weet u over amberlicht?')
        assert fact in str(providers['ollama'].calls[-1])
        memories=c.get('/api/v1/natural/memory').json()['items']
        assert len(memories)==1
        assert c.delete('/api/v1/natural/memory/'+memories[0]['id']).status_code==200
        chat(c,'Wat weet u over amberlicht?',conversation_id=second['conversation_id'])
        assert fact not in str(providers['ollama'].calls[-1])
        patch(c,'memory',{'history':False})
        chat(c,'Ik ontwerp project privélicht.')
        chat(c,'Wat weet u over privélicht?')
        assert 'Ik ontwerp project privélicht.' not in str(providers['ollama'].calls[-1])
        with app.state.natural.store.database.connection() as db:
            assert db.execute('SELECT count(*) FROM natural_forgotten WHERE source_turn IN (SELECT id FROM chat_turns WHERE conversation_id=?)',(original['conversation_id'],)).fetchone()[0]


def test_episode_fts_migration_indexes_old_history_and_tracks_edits(tmp_path):
    database=Database(tmp_path/'v8.sqlite3');database.initialize()
    with database.connection() as db:
        for trigger in ('natural_episode_insert','natural_episode_delete','natural_episode_update'):
            db.execute('DROP TRIGGER '+trigger)
        for table in ('natural_episode_sources','natural_episode_origins','natural_episode_fts'):
            db.execute('DROP TABLE '+table)
        db.execute('DELETE FROM schema_migrations WHERE version=9')
        db.execute('PRAGMA user_version=8')
        db.execute("INSERT INTO chat_conversations VALUES ('c','test','now','now')")
        db.execute("INSERT INTO chat_turns(id,conversation_id,created_at,user_text,status,sequence) VALUES ('t','c','now','oudonderwerp','completed',1)")
    database.close();database.initialize()
    with database.connection() as db:
        assert db.execute("SELECT count(*) FROM natural_episode_fts WHERE natural_episode_fts MATCH 'oudonderwerp'").fetchone()[0]==1
        db.execute("UPDATE chat_turns SET user_text='nieuwonderwerp' WHERE id='t'")
        assert db.execute("SELECT count(*) FROM natural_episode_fts WHERE natural_episode_fts MATCH 'oudonderwerp'").fetchone()[0]==0
        db.execute("DELETE FROM chat_conversations WHERE id='c'")
        assert db.execute("SELECT count(*) FROM natural_episode_fts WHERE natural_episode_fts MATCH 'nieuwonderwerp'").fetchone()[0]==0
    assert list(tmp_path.glob(f'v8.sqlite3.pre-v{SCHEMA_VERSION}-*.bak'))


def test_episode_sync_owner_and_revocation_boundaries(settings):
    app,providers=build(settings)
    original='Mijn hobbyproject maansteen gebruikt bamboe.'
    with client(app) as c:
        patch(c,'memory',{'episodes':True,'synchronize':False})
        first=chat(c,original)
        chat(c,'Vertel over maansteen')
        assert original in str(providers['ollama'].calls[-1])
        with app.state.natural.store.database.connection() as db:
            db.execute("UPDATE natural_episode_origins SET device_id='another-device' WHERE turn_id IN (SELECT id FROM chat_turns WHERE conversation_id=?)",(first['conversation_id'],))
        chat(c,'Vertel over maansteen')
        assert original not in str(providers['ollama'].calls[-1])
        patch(c,'memory',{'synchronize':True})
        chat(c,'Vertel over maansteen')
        assert original in str(providers['ollama'].calls[-1])
        with app.state.natural.store.database.connection() as db:
            db.execute('UPDATE natural_conversation_owners SET user_id=999 WHERE conversation_id=?',(first['conversation_id'],))
        chat(c,'Vertel over maansteen')
        assert original not in str(providers['ollama'].calls[-1])
