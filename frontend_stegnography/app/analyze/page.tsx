"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, Eye } from "lucide-react"

export default function AnalyzeLab() {
    const [image, setImage] = useState<File | null>(null)
    const [imagePreview, setImagePreview] = useState<string | null>(null)
    const [bitPlane, setBitPlane] = useState([0])
    const [channel, setChannel] = useState<'R' | 'G' | 'B'>('R')
    const [visualizationUrl, setVisualizationUrl] = useState<string | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            setImage(file)
            setImagePreview(URL.createObjectURL(file))
            setVisualizationUrl(null)
        }
    }

    const handleVisualize = async () => {
        if (!image) return

        setIsProcessing(true)
        try {
            const formData = new FormData()
            formData.append('file', image)
            formData.append('bit_plane', bitPlane[0].toString())
            formData.append('channel', channel)

            const response = await fetch('http://localhost:5000/stego/visualize', {
                method: 'POST',
                body: formData
            })

            if (!response.ok) throw new Error('Visualization failed')
            const blob = await response.blob()
            setVisualizationUrl(URL.createObjectURL(blob))
        } catch (error) {
            console.error(error)
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="grid gap-6 lg:grid-cols-12 h-[calc(100vh-8rem)]">
            {/* Controls */}
            <div className="lg:col-span-4 flex flex-col gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Source Image</CardTitle>
                        <CardDescription>Select image to analyze</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="border-2 border-dashed border-muted-foreground/25 hover:border-primary transition-colors aspect-square rounded-lg flex items-center justify-center bg-muted/50 relative overflow-hidden group cursor-pointer">
                            {imagePreview ? (
                                <img src={imagePreview} alt="Source" className="object-contain w-full h-full" />
                            ) : (
                                <div className="text-center p-4">
                                    <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                                    <p className="text-sm font-mono text-muted-foreground">SELECT IMAGE</p>
                                </div>
                            )}
                            <input type="file" accept="image/*" className="absolute inset-0 opacity-0 cursor-pointer" onChange={handleImageUpload} />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Analysis Parameters</CardTitle>
                        <CardDescription>Configure bit plane extraction</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-3">
                            <label className="text-sm font-medium">Channel</label>
                            <Select value={channel} onValueChange={(v) => setChannel(v as any)}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select channel" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="R">Red Channel</SelectItem>
                                    <SelectItem value="G">Green Channel</SelectItem>
                                    <SelectItem value="B">Blue Channel</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-sm font-medium">Bit Plane</label>
                                <Badge variant="outline">Bit {bitPlane[0]}</Badge>
                            </div>
                            <Slider
                                min={0}
                                max={7}
                                step={1}
                                value={bitPlane}
                                onValueChange={setBitPlane}
                            />
                            <div className="flex justify-between text-xs text-muted-foreground font-mono">
                                <span>LSB (0)</span>
                                <span>MSB (7)</span>
                            </div>
                        </div>

                        <Button className="w-full" disabled={!image || isProcessing} onClick={handleVisualize}>
                            <Eye className="mr-2 h-4 w-4" />
                            {isProcessing ? "RENDERING..." : "RENDER PLANE"}
                        </Button>
                    </CardContent>
                </Card>
            </div>

            {/* Visualization */}
            <div className="lg:col-span-8 h-full">
                <Card className="h-full flex flex-col">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle>Bit Plane Visualization</CardTitle>
                        {visualizationUrl && (
                            <div className="flex gap-2">
                                <Badge variant="secondary">CH: {channel}</Badge>
                                <Badge variant="secondary">BIT: {bitPlane[0]}</Badge>
                            </div>
                        )}
                    </CardHeader>
                    <CardContent className="flex-1 bg-black/95 rounded-md m-6 flex items-center justify-center overflow-hidden relative border border-white/10">
                        {visualizationUrl ? (
                            <img src={visualizationUrl} alt="Visualization" className="object-contain max-w-full max-h-full" />
                        ) : (
                            <div className="text-muted-foreground font-mono text-center">
                                <p className="mb-2">NO VISUALIZATION RENDERED</p>
                                <p className="text-xs text-muted-foreground/60">Select parameters and click Render to view bit planes</p>
                            </div>
                        )}

                        {/* Grid overlay */}
                        <div className="absolute inset-0 pointer-events-none opacity-10"
                            style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '20px 20px' }}
                        />
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
