'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export default function ConnectPlatformButton({ 
  platform, 
  name 
}: { 
  platform: string
  name: string
}) {
  const [isConnecting, setIsConnecting] = useState(false)
  const [showUsernameInput, setShowUsernameInput] = useState(false)
  const [username, setUsername] = useState('')

  const handleConnect = async () => {
    if (!showUsernameInput) {
      setShowUsernameInput(true)
      return
    }

    if (!username.trim()) {
      alert('Please enter a username')
      return
    }

    setIsConnecting(true)
    console.log('[v0] Connecting platform:', platform, 'with username:', username)

    try {
      const supabase = createClient()
      
      // Get current user
      const { data: { user } } = await supabase.auth.getUser()
      
      if (!user) {
        throw new Error('Not authenticated')
      }

      // Save connection to database
      const { error } = await supabase
        .from('oauth_connections')
        .upsert({
          user_id: user.id,
          platform,
          platform_username: username,
          is_active: true,
          connected_at: new Date().toISOString(),
        }, {
          onConflict: 'user_id,platform'
        })

      if (error) throw error

      console.log('[v0] Platform connected successfully')
      window.location.reload()
    } catch (error) {
      console.error('[v0] Error connecting platform:', error)
      alert('Failed to connect platform. Please try again.')
    } finally {
      setIsConnecting(false)
    }
  }

  if (!showUsernameInput) {
    return (
      <button
        onClick={handleConnect}
        className="text-sm text-primary hover:underline"
      >
        Connect
      </button>
    )
  }

  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground mb-1">
        Enter their public {name} username (e.g., @username)
      </div>
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder={`@username`}
        className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        disabled={isConnecting}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            handleConnect()
          }
        }}
      />
      <button
        onClick={handleConnect}
        disabled={isConnecting}
        className="w-full text-sm bg-primary text-primary-foreground rounded-lg py-2 hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        {isConnecting ? 'Analyzing profile...' : 'Add Profile'}
      </button>
      <button
        onClick={() => setShowUsernameInput(false)}
        className="w-full text-xs text-muted-foreground hover:text-foreground"
      >
        Cancel
      </button>
    </div>
  )
}
