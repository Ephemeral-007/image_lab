"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Activity, Shield, Zap, Database, Lock, FileText } from "lucide-react"
import Link from "next/link"

export default function Dashboard() {
  const [stats, setStats] = useState({
    encoded_count: 0,
    decoded_count: 0,
    total_bytes_processed: 0,
    active_sessions: 1
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('http://localhost:5000/stats')
        if (res.ok) {
          const data = await res.json()
          setStats(data)
        }
      } catch (e) {
        console.error("Failed to fetch stats", e)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Research Dashboard</h1>
          <p className="text-muted-foreground font-mono mt-1">System Status: OPERATIONAL | v2.1.0</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline" className="font-mono">AES-256-GCM</Badge>
          <Badge className="bg-green-600 hover:bg-green-700 font-mono">SECURE</Badge>
        </div>
      </div>

      <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard title="Total Encoded" value={stats.encoded_count} icon={Database} description="Images processed" />
        <StatsCard title="Data Processed" value={formatBytes(stats.total_bytes_processed)} icon={Shield} description="Total throughput" />
        <StatsCard title="Total Decoded" value={stats.decoded_count} icon={Zap} description="Extractions performed" />
        <StatsCard title="Active Sessions" value={stats.active_sessions} icon={Activity} description="Current researchers" />
      </div>

      <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-1 md:col-span-2 lg:col-span-4">
          <CardHeader>
            <CardTitle>Quick Access Workbench</CardTitle>
            <CardDescription>Launch primary research tools</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <Link href="/encode">
              <Button variant="outline" className="w-full h-24 flex flex-col gap-2 items-center justify-center text-lg hover:border-primary hover:bg-accent/50 transition-all">
                <Zap className="h-8 w-8" />
                Encode Lab
              </Button>
            </Link>
            <Link href="/decode">
              <Button variant="outline" className="w-full h-24 flex flex-col gap-2 items-center justify-center text-lg hover:border-primary hover:bg-accent/50 transition-all">
                <Lock className="h-8 w-8" />
                Decode Lab
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="col-span-1 md:col-span-2 lg:col-span-3">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest system operations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { action: "System Start", file: "Backend Service", time: "Just now", status: "Online" },
                { action: "Stats Init", file: "Metrics Engine", time: "Just now", status: "Active" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between border-b pb-2 last:border-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-muted rounded-full">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{item.action}</p>
                      <p className="text-xs text-muted-foreground font-mono">{item.file}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary" className="text-[10px]">{item.status}</Badge>
                    <p className="text-xs text-muted-foreground mt-1">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatsCard({ title, value, icon: Icon, description }: any) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold font-mono">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}
