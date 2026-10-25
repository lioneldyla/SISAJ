from fastapi.testclient import TestClient
from app.main import app
from tests.test_dashboard import context,case

def test_all_cabinets_remain_available_when_one_is_selected():
    with TestClient(app) as c:
        h=context(c);case(c,h,'SYNTH-A','Cabinet A');case(c,h,'SYNTH-B','Cabinet B')
        d=c.get('/dashboard/analysis',headers=h).json()
        assert sum(x['cases'] for x in d['by_cabinet'])==2
        assert {x['label'] for x in d['by_cabinet']}=={'Cabinet A','Cabinet B'}
        one=c.get('/dashboard/analysis?cabinet=Cabinet%20A',headers=h).json()
        assert one['cohort_size']==1
        assert one['options']['cabinet']==['Cabinet A','Cabinet B']
        assert one['by_cabinet'][0]['cases']==1
        assert len(d['indicator_catalogue'])==63
        assert len({x['code'] for x in d['indicator_catalogue']})==63
        assert next(x for x in d['indicator_catalogue'] if x['code']=='PEN-01')['available'] is False
        assert next(x for x in d['cards'] if x['key']=='stock')['value'] is None
        assert next(x for x in d['cards'] if x['key']=='decisions')['value']==2
        assert c.get('/dashboard/analysis?metric=decisions',headers=h).json()['total']==2
        assert 'Données fictives' not in d['population']
        for entry in d['indicator_catalogue']:
            if entry['available']:assert entry['metric'] in {x['key'] for x in d['cards']}
