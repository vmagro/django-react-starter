from .query import Query


def test_execute():
    query = Query('''
    {
        profiles(id: 1) {
            username
        }
        posts {
            title
            vote_count
            owner {
                username
            }
        }
    }''')
    result = query.execute()['data']
    assert 'posts' in result
    assert False
