import { useEffect, lazy, Suspense } from 'react'
import { useWorkspaceStore } from '../store/workspace.store'
import { useLayoutStore } from '../store/layout.store'
import { getPreset } from './layout_presets'
import { Panel } from './Panel'

const AvatarPanel = lazy(() => import('../components/AvatarPanel'))
const NeuralMapPanel = lazy(() => import('../components/NeuralMapPanel'))
const BrokerWorkspace = lazy(() => import('../workspaces/broker'))
const BusinessWorkspace = lazy(() => import('../workspaces/business'))
const CodingWorkspace = lazy(() => import('../workspaces/coding'))
const OSWorkspace = lazy(() => import('../workspaces/os'))

const WORKSPACE_PANELS: Record<string, React.ComponentType> = {
  broker: BrokerWorkspace,
  business: BusinessWorkspace,
  coding: CodingWorkspace,
  os: OSWorkspace,
}

export function PanelManager() {
  const active = useWorkspaceStore((s) => s.active)
  const avatarRenderer = useWorkspaceStore((s) => s.avatarRenderer)
  const neuralMapMode = useWorkspaceStore((s) => s.neuralMapMode)
  const { loadFromStorage } = useLayoutStore()

  useEffect(() => {
    document.body.dataset.workspace = active
    loadFromStorage(active, getPreset(active))
  }, [active, loadFromStorage])

  const WorkspaceContent = WORKSPACE_PANELS[active]

  return (
    <div className="fixed inset-0">
      <Suspense fallback={null}>
        {/* Workspace-specific panels */}
        <WorkspaceContent />

        {/* Persistent panels — always present, never destroyed */}
        <Panel id="avatar" title="Avatar" noPad>
          <AvatarPanel renderer={avatarRenderer} />
        </Panel>

        <Panel id="neural-map" title="Neural Map" noPad>
          <NeuralMapPanel mode={neuralMapMode} />
        </Panel>
      </Suspense>
    </div>
  )
}
