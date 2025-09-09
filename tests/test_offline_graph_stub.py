from app.services.graph_client import GraphClient

def test_offline_send_mail():
    c = GraphClient()
    mid = c.send_mail('me', ['a@ex.com'], [], 's', '<b>hi</b>')
    assert mid == 'offline-simulated'
