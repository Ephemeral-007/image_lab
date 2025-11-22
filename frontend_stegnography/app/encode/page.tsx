"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { toast } from "sonner"
import { Upload, FileText, Lock, Image as ImageIcon, Zap, Save } from "lucide-react"

export default function EncodeLab() {
    // Image State
    const [coverImage, setCoverImage] = useState<File | null>(null)
    const [coverPreview, setCoverPreview] = useState<string | null>(null)
    const [imageStats, setImageStats] = useState<{ width: number; height: number; format: string; size: number } | null>(null)

    // Data State
    const [activeTab, setActiveTab] = useState<"text" | "file">("text")
    const [secretText, setSecretText] = useState("")
    const [secretFile, setSecretFile] = useState<File | null>(null)

    // Parameters
    const [bitsPerChannel, setBitsPerChannel] = useState([1])
    const [channels, setChannels] = useState<string[]>(["R", "G", "B"])
    const [useEncryption, setUseEncryption] = useState(false)
    const [password, setPassword] = useState("")
    const [compress, setCompress] = useState(false)

    // Analysis State
    const [maxCapacity, setMaxCapacity] = useState(0)
    const [currentSize, setCurrentSize] = useState(0)
    const [isProcessing, setIsProcessing] = useState(false)
    const [result, setResult] = useState<any>(null)

    // Calculate Capacity
    useEffect(() => {
        if (imageStats) {
            const pixels = imageStats.width * imageStats.height
            const channelCount = channels.length
            const totalBits = pixels * channelCount * bitsPerChannel[0]
            const capacityBytes = Math.floor(totalBits / 8)
            const usableCapacity = Math.max(0, capacityBytes - 100) // Overhead buffer
            setMaxCapacity(usableCapacity)
        }
    }, [imageStats, bitsPerChannel, channels])

    // Calculate Payload Size
    useEffect(() => {
        let size = 0
        if (activeTab === "text") {
            size = new Blob([secretText]).size
        } else if (secretFile) {
            size = secretFile.size
        }

        if (useEncryption) size += 48 // Salt + IV overhead
        if (compress) size = Math.ceil(size * 0.9) // Rough estimate

        setCurrentSize(size)
    }, [secretText, secretFile, activeTab, useEncryption, compress])

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            setCoverImage(file)
            const url = URL.createObjectURL(file)
            setCoverPreview(url)

            const img = new Image()
            img.onload = () => {
                setImageStats({
                    width: img.width,
                    height: img.height,
                    format: file.type.split('/')[1].toUpperCase(),
                    size: file.size
                })
            }
            img.src = url
        }
    }

    const handleEncode = async () => {
        if (!coverImage) return

        setIsProcessing(true)
        try {
            const formData = new FormData()
            formData.append('file', coverImage)

            if (activeTab === "text") {
                formData.append('text', secretText)
                if (useEncryption && password) formData.append('password', password)
                formData.append('bits_per_channel', bitsPerChannel[0].toString())

                const response = await fetch('http://localhost:5000/stego/hide-text', {
                    method: 'POST',
                    body: formData
                })

                if (!response.ok) throw new Error('Encoding failed')
                const data = await response.json()
                setResult(data)
                toast.success("Encoding Complete")
            } else {
                formData.append('cover', coverImage)
                formData.append('secret', secretFile!)
                if (useEncryption && password) formData.append('password', password)
                formData.append('bits_per_channel', bitsPerChannel[0].toString())

                const response = await fetch('http://localhost:5000/stego/hide-file', {
                    method: 'POST',
                    body: formData
                })

                if (!response.ok) throw new Error('Encoding failed')
                const data = await response.json()
                setResult(data)
                toast.success("Encoding Complete")
            }
        } catch (error) {
            console.error(error)
            toast.error("Operation Failed")
        } finally {
            setIsProcessing(false)
        }
    }

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
    }

    const capacityPercentage = maxCapacity > 0 ? Math.min((currentSize / maxCapacity) * 100, 100) : 0

    return (
        <div className="grid gap-6 lg:grid-cols-12 h-[calc(100vh-8rem)]">
            {/* Left Panel: Source & Payload */}
            <div className="lg:col-span-4 flex flex-col gap-6 overflow-y-auto pr-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Source Image</CardTitle>
                        <CardDescription>Upload cover image</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="border-2 border-dashed border-muted-foreground/25 hover:border-primary transition-colors aspect-video rounded-lg flex items-center justify-center bg-muted/50 relative overflow-hidden group cursor-pointer">
                            {coverPreview ? (
                                <img src={coverPreview} alt="Cover" className="object-contain w-full h-full" />
                            ) : (
                                <div className="text-center p-4">
                                    <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                                    <p className="text-xs font-mono text-muted-foreground">DROP IMAGE HERE</p>
                                </div>
                            )}
                            <input type="file" accept="image/*" className="absolute inset-0 opacity-0 cursor-pointer" onChange={handleImageUpload} />
                        </div>

                        {imageStats && (
                            <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-mono">
                                <div className="bg-muted p-2 rounded">
                                    <span className="text-muted-foreground block">DIMENSIONS</span>
                                    {imageStats.width} x {imageStats.height}
                                </div>
                                <div className="bg-muted p-2 rounded">
                                    <span className="text-muted-foreground block">SIZE</span>
                                    {formatBytes(imageStats.size)}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>Payload Data</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Tabs defaultValue="text" onValueChange={(v) => setActiveTab(v as "text" | "file")}>
                            <TabsList className="w-full mb-4">
                                <TabsTrigger value="text" className="flex-1">Text</TabsTrigger>
                                <TabsTrigger value="file" className="flex-1">File</TabsTrigger>
                            </TabsList>

                            <TabsContent value="text">
                                <textarea
                                    className="w-full h-32 p-3 text-sm font-mono bg-background border rounded-md focus:ring-1 focus:ring-primary outline-none resize-none"
                                    placeholder="Enter secret message..."
                                    value={secretText}
                                    onChange={(e) => setSecretText(e.target.value)}
                                />
                            </TabsContent>

                            <TabsContent value="file">
                                <div className="border-2 border-dashed border-muted-foreground/25 p-8 text-center rounded-lg hover:bg-muted/50 relative cursor-pointer">
                                    <FileText className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                                    <p className="text-sm font-mono">{secretFile ? secretFile.name : "Select File to Embed"}</p>
                                    <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => setSecretFile(e.target.files?.[0] || null)} />
                                </div>
                            </TabsContent>
                        </Tabs>

                        <div className="mt-4 flex justify-between items-center">
                            <span className="text-xs font-mono text-muted-foreground">PAYLOAD SIZE</span>
                            <Badge variant="secondary" className="font-mono">{formatBytes(currentSize)}</Badge>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Middle Panel: Configuration */}
            <div className="lg:col-span-4 flex flex-col gap-6 overflow-y-auto pr-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Algorithm Parameters</CardTitle>
                        <CardDescription>Configure steganography settings</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-8">
                        {/* Bit Depth */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <label className="text-sm font-medium">LSB Depth</label>
                                <Badge variant="outline">{bitsPerChannel[0]} Bits</Badge>
                            </div>
                            <Slider
                                min={1}
                                max={8}
                                step={1}
                                value={bitsPerChannel}
                                onValueChange={setBitsPerChannel}
                                className="w-full"
                            />
                            <p className="text-xs text-muted-foreground">
                                Higher depth = more capacity, less quality.
                            </p>
                        </div>

                        {/* Channels */}
                        <div className="space-y-3">
                            <label className="text-sm font-medium">Active Channels</label>
                            <div className="flex gap-2">
                                {['R', 'G', 'B'].map(channel => (
                                    <Button
                                        key={channel}
                                        variant={channels.includes(channel) ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setChannels(prev => prev.includes(channel) ? prev.filter(c => c !== channel) : [...prev, channel])}
                                        className="w-10 font-mono"
                                    >
                                        {channel}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Security */}
                        <div className="space-y-4 pt-4 border-t">
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <label className="text-sm font-medium">Encryption</label>
                                    <p className="text-xs text-muted-foreground">AES-256-GCM protection</p>
                                </div>
                                <Switch checked={useEncryption} onCheckedChange={setUseEncryption} />
                            </div>

                            {useEncryption && (
                                <div className="relative">
                                    <Lock className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        type="password"
                                        placeholder="Enter passphrase"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="pl-9 font-mono"
                                    />
                                </div>
                            )}
                        </div>

                        {/* Compression */}
                        <div className="flex items-center justify-between pt-4 border-t">
                            <div className="space-y-0.5">
                                <label className="text-sm font-medium">Compression</label>
                                <p className="text-xs text-muted-foreground">ZLIB compression</p>
                            </div>
                            <Switch checked={compress} onCheckedChange={setCompress} />
                        </div>
                    </CardContent>
                </Card>

                <Button
                    size="lg"
                    className="w-full font-mono text-lg h-14"
                    disabled={!coverImage || isProcessing || currentSize > maxCapacity}
                    onClick={handleEncode}
                >
                    {isProcessing ? "PROCESSING..." : "RUN ENCODE PROCESS"}
                </Button>
            </div>

            {/* Right Panel: Analysis */}
            <div className="lg:col-span-4 flex flex-col gap-6 overflow-y-auto">
                <Card>
                    <CardHeader>
                        <CardTitle>Capacity Analysis</CardTitle>
                        <CardDescription>Real-time metrics</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Capacity Meter */}
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs font-mono">
                                <span>USAGE</span>
                                <span>{capacityPercentage.toFixed(1)}%</span>
                            </div>
                            <Progress value={capacityPercentage} className={currentSize > maxCapacity ? "bg-red-100 [&>div]:bg-red-600" : ""} />
                            <div className="flex justify-between text-xs font-mono text-muted-foreground">
                                <span>{formatBytes(currentSize)}</span>
                                <span>MAX: {formatBytes(maxCapacity)}</span>
                            </div>
                        </div>

                        {/* Theoretical Metrics */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 border rounded-lg bg-muted/20">
                                <div className="text-xs text-muted-foreground font-mono mb-1">EST. PSNR</div>
                                <div className="text-2xl font-bold font-mono">
                                    {bitsPerChannel[0] === 1 ? '> 51' : bitsPerChannel[0] <= 2 ? '> 44' : '< 40'} <span className="text-xs font-normal">dB</span>
                                </div>
                            </div>
                            <div className="p-4 border rounded-lg bg-muted/20">
                                <div className="text-xs text-muted-foreground font-mono mb-1">EST. MSE</div>
                                <div className="text-2xl font-bold font-mono">
                                    {bitsPerChannel[0] === 1 ? '< 0.5' : bitsPerChannel[0] <= 2 ? '< 2.0' : '> 5.0'}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {result && (
                    <Card className="bg-primary text-primary-foreground border-primary">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Save className="h-5 w-5" />
                                Process Complete
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="aspect-video bg-black/20 rounded-lg flex items-center justify-center overflow-hidden relative border border-white/10">
                                <img src={`http://localhost:5000/${result.output_path}`} alt="Result" className="object-contain w-full h-full" />
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs font-mono opacity-80">
                                <div>USED: {result.used_capacity_bits} bits</div>
                                <div>ENC: {result.encrypted ? 'YES' : 'NO'}</div>
                            </div>
                            <a
                                href={`http://localhost:5000/${result.output_path}`}
                                download
                                className="block w-full bg-background text-foreground text-center py-3 rounded-md font-bold font-mono hover:bg-accent transition-colors"
                            >
                                DOWNLOAD RESULT
                            </a>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
