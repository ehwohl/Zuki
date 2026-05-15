import { useEffect } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'
import WorldMap from './WorldMap'
import NewsFeed from './NewsFeed'
import Watchlist from './Watchlist'

export default function BrokerWorkspace() {
  // Signal backend to route window profile
  useEffect(() => {
    bridge.send('navigate', { workspace: 'broker' })
  }, [])

  return (
    <>
      <Panel id="world-map" title="War Room — Global Markets" noPad>
        <WorldMap />
      </Panel>
      <Panel id="news-feed" title="Intel Feed" noPad>
        <NewsFeed />
      </Panel>
      <Panel id="watchlist" title="Watchlist" noPad>
        <Watchlist />
      </Panel>
    </>
  )
}
