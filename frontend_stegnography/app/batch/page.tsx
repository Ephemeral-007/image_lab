"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { FileCode } from "lucide-react"

export default function BatchPage() {
    return (
        <div className="flex flex-col gap-6 h-[calc(100vh-8rem)]">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Batch Processing</h1>
                    <p className="text-muted-foreground font-mono mt-1">Bulk steganography operations</p>
                </div>
            </div>

            <div className="flex-1 flex items-center justify-center">
                <Card className="w-full max-w-md">
                    <CardHeader className="text-center">
                        <div className="mx-auto bg-muted p-4 rounded-full mb-4">
                            <FileCode className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <CardTitle>Module Under Development</CardTitle>
                        <CardDescription>
                            Batch processing capabilities for multi-file encoding/decoding are coming in version 2.2.0.
                        </CardDescription>
                    </CardHeader>
                </Card>
            </div>
        </div>
    )
}
