"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Upload, BarChart3, FileDigit } from "lucide-react"
import { toast } from "sonner"

export default function CapacityPage() {
    const [image, setImage] = useState<File | null>(null)
    const [preview, setPreview] = useState<string | null>(null)
    const [data, setData] = useState<any>(null)
    const [isProcessing, setIsProcessing] = useState(false)

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            setImage(file)
            setPreview(URL.createObjectURL(file))
            setData(null)

            // Auto-analyze
            setIsProcessing(true)
            try {
                const formData = new FormData()
                formData.append('file', file)

                const res = await fetch('http://localhost:5000/stego/capacity', {
                    method: 'POST',
                    body: formData
                })

                if (!res.ok) throw new Error("Analysis failed")
                const result = await res.json()
                setData(result)
                toast.success("Capacity Analysis Complete")
            } catch (error) {
                console.error(error)
                toast.error("Failed to analyze image")
            } finally {
                setIsProcessing(false)
            }
        }
    }

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
    }

    return (
        <div className="flex flex-col gap-6 h-[calc(100vh-8rem)] overflow-y-auto">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Capacity Metrics</h1>
                    <p className="text-muted-foreground font-mono mt-1">Bit-depth analysis engine</p>
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-12">
                {/* Upload Section */}
                <div className="lg:col-span-4 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Source Analysis</CardTitle>
                            <CardDescription>Upload image to calculate capacity</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="border-2 border-dashed border-muted-foreground/25 hover:border-primary transition-colors aspect-square rounded-lg flex items-center justify-center bg-muted/50 relative overflow-hidden group cursor-pointer">
                                {preview ? (
                                    <img src={preview} alt="Preview" className="object-contain w-full h-full" />
                                ) : (
                                    <div className="text-center p-4">
                                        <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                                        <p className="text-sm font-mono text-muted-foreground">SELECT IMAGE</p>
                                    </div>
                                )}
                                <input type="file" accept="image/*" className="absolute inset-0 opacity-0 cursor-pointer" onChange={handleUpload} />
                            </div>

                            {isProcessing && (
                                <div className="mt-4 text-center font-mono text-sm animate-pulse">
                                    CALCULATING METRICS...
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Results Section */}
                <div className="lg:col-span-8 space-y-6">
                    {data ? (
                        <>
                            <Card>
                                <CardHeader>
                                    <CardTitle>Capacity Distribution</CardTitle>
                                    <CardDescription>Storage capacity vs Bit Depth</CardDescription>
                                </CardHeader>
                                <CardContent className="h-[300px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={data.capacity}>
                                            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                                            <XAxis dataKey="bits" label={{ value: 'Bits per Channel', position: 'insideBottom', offset: -5 }} />
                                            <YAxis tickFormatter={(val) => formatBytes(val)} />
                                            <Tooltip
                                                formatter={(val: number) => [formatBytes(val), "Capacity"]}
                                                labelFormatter={(label) => `${label} Bit(s) Depth`}
                                                contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                                            />
                                            <Bar dataKey="bytes" fill="currentColor" className="fill-primary" radius={[4, 4, 0, 0]}>
                                                {data.capacity.map((entry: any, index: number) => (
                                                    <Cell key={`cell-${index}`} fillOpacity={0.6 + (index * 0.05)} />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>Detailed Metrics</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead className="w-[100px]">Depth</TableHead>
                                                <TableHead>Total Capacity</TableHead>
                                                <TableHead>Efficiency</TableHead>
                                                <TableHead className="text-right">Est. Quality (PSNR)</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {data.capacity.map((row: any) => (
                                                <TableRow key={row.bits}>
                                                    <TableCell className="font-medium">{row.bits} Bit</TableCell>
                                                    <TableCell className="font-mono">{formatBytes(row.bytes)}</TableCell>
                                                    <TableCell>{(row.bits / 8 * 100).toFixed(1)}%</TableCell>
                                                    <TableCell className="text-right font-mono">
                                                        {row.bits === 1 ? '> 51 dB' : row.bits <= 2 ? '> 44 dB' : row.bits <= 4 ? '> 30 dB' : '< 20 dB'}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </CardContent>
                            </Card>
                        </>
                    ) : (
                        <Card className="h-full flex items-center justify-center border-dashed">
                            <div className="text-center p-8 text-muted-foreground">
                                <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-20" />
                                <h3 className="text-lg font-medium">No Data Available</h3>
                                <p className="text-sm">Upload an image to view capacity analysis</p>
                            </div>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    )
}
