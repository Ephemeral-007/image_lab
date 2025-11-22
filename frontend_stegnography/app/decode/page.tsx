"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { Upload, Lock, FileCheck, Copy } from "lucide-react"

export default function DecodeLab() {
    const [stegoImage, setStegoImage] = useState<File | null>(null)
    const [stegoPreview, setStegoPreview] = useState<string | null>(null)
    const [password, setPassword] = useState("")
    const [isProcessing, setIsProcessing] = useState(false)
    const [result, setResult] = useState<any>(null)

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            setStegoImage(file)
            setStegoPreview(URL.createObjectURL(file))
            setResult(null)
        }
    }

    const handleDecode = async () => {
        if (!stegoImage) return

        setIsProcessing(true)
        try {
            const formData = new FormData()
            formData.append('file', stegoImage)
            if (password) formData.append('password', password)

            const response = await fetch('http://localhost:5000/stego/reveal-text', {
                method: 'POST',
                body: formData
            })

            if (!response.ok) throw new Error('Decoding failed')
            const data = await response.json()
            setResult(data)
            toast.success("Decoding Complete")
        } catch (error) {
            console.error(error)
            toast.error("Decoding Failed - Check Password or Image")
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="grid gap-6 lg:grid-cols-12 h-[calc(100vh-8rem)]">
            {/* Left: Source */}
            <div className="lg:col-span-5 flex flex-col gap-6">
                <Card className="h-full flex flex-col">
                    <CardHeader>
                        <CardTitle>Steganographic Source</CardTitle>
                        <CardDescription>Upload image to extract data</CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 flex flex-col gap-6">
                        <div className="border-2 border-dashed border-muted-foreground/25 hover:border-primary transition-colors flex-1 rounded-lg flex items-center justify-center bg-muted/50 relative overflow-hidden group cursor-pointer min-h-[300px]">
                            {stegoPreview ? (
                                <img src={stegoPreview} alt="Stego" className="object-contain w-full h-full" />
                            ) : (
                                <div className="text-center p-4">
                                    <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                                    <p className="text-sm font-mono text-muted-foreground">DROP STEGO IMAGE</p>
                                </div>
                            )}
                            <input type="file" accept="image/*" className="absolute inset-0 opacity-0 cursor-pointer" onChange={handleImageUpload} />
                        </div>

                        <div className="space-y-4">
                            <div className="relative">
                                <Lock className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                <Input
                                    type="password"
                                    placeholder="Decryption Key (Optional)"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pl-9 font-mono"
                                />
                            </div>
                            <Button className="w-full h-12 text-lg" disabled={!stegoImage || isProcessing} onClick={handleDecode}>
                                {isProcessing ? "EXTRACTING..." : "EXTRACT DATA"}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Right: Results */}
            <div className="lg:col-span-7 flex flex-col gap-6">
                <Card className="h-full flex flex-col">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle>Extraction Result</CardTitle>
                            <CardDescription>Recovered payload</CardDescription>
                        </div>
                        {result && <Badge variant="outline" className="text-green-600 border-green-600 bg-green-50">SUCCESS</Badge>}
                    </CardHeader>
                    <CardContent className="flex-1">
                        {result ? (
                            <div className="space-y-4 h-full flex flex-col">
                                {result.text ? (
                                    <>
                                        <div className="flex-1 bg-muted/50 border rounded-md p-4 font-mono text-sm overflow-auto whitespace-pre-wrap">
                                            {result.text}
                                        </div>
                                        <div className="flex justify-end gap-2">
                                            <Button variant="outline" onClick={() => {
                                                navigator.clipboard.writeText(result.text)
                                                toast.success("Copied to clipboard")
                                            }}>
                                                <Copy className="h-4 w-4 mr-2" />
                                                COPY TO CLIPBOARD
                                            </Button>
                                        </div>
                                    </>
                                ) : result.filename ? (
                                    <div className="flex-1 flex flex-col items-center justify-center bg-muted/30 border rounded-md">
                                        <FileCheck className="h-16 w-16 mb-4 text-primary" />
                                        <h3 className="text-xl font-bold font-mono">{result.filename}</h3>
                                        <p className="text-muted-foreground font-mono text-sm mt-2">FILE RECOVERED SUCCESSFULLY</p>
                                        <Button className="mt-6">DOWNLOAD FILE</Button>
                                    </div>
                                ) : (
                                    <div className="flex-1 flex items-center justify-center text-muted-foreground font-mono">
                                        NO DATA FOUND
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground/50 font-mono text-lg border-2 border-dashed border-muted rounded-lg">
                                <Lock className="h-12 w-12 mb-4 opacity-20" />
                                WAITING FOR EXTRACTION...
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
