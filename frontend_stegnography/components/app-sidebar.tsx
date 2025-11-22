"use client"

import * as React from "react"
import {
    AudioWaveform,
    BookOpen,
    Bot,
    Command,
    Frame,
    GalleryVerticalEnd,
    Map,
    PieChart,
    Settings2,
    SquareTerminal,
    Zap,
    Search,
    Lock,
    Eye,
    BarChart3,
    Home,
    FileCode
} from "lucide-react"

import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarRail,
    SidebarGroup,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuItem,
    SidebarMenuButton,
} from "@/components/ui/sidebar"
import { usePathname } from "next/navigation"
import Link from "next/link"

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
    const pathname = usePathname()

    const navMain = [
        {
            title: "Workbench",
            url: "#",
            icon: SquareTerminal,
            isActive: true,
            items: [
                {
                    title: "Dashboard",
                    url: "/",
                    icon: Home,
                },
                {
                    title: "Encode Lab",
                    url: "/encode",
                    icon: Zap,
                },
                {
                    title: "Decode Lab",
                    url: "/decode",
                    icon: Lock,
                },
                {
                    title: "Bit Analysis",
                    url: "/analyze",
                    icon: Eye,
                },
            ],
        },
        {
            title: "Research",
            url: "#",
            icon: BookOpen,
            items: [
                {
                    title: "Capacity Metrics",
                    url: "/capacity",
                    icon: BarChart3,
                },
                {
                    title: "Batch Processing",
                    url: "/batch",
                    icon: FileCode,
                },
            ],
        },
    ]

    return (
        <Sidebar collapsible="icon" {...props}>
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" asChild>
                            <Link href="/">
                                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                                    <Command className="size-4" />
                                </div>
                                <div className="grid flex-1 text-left text-sm leading-tight">
                                    <span className="truncate font-semibold">ImageLab</span>
                                    <span className="truncate text-xs">Research Edition</span>
                                </div>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>
            <SidebarContent>
                {navMain.map((group) => (
                    <SidebarGroup key={group.title}>
                        <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
                        <SidebarMenu>
                            {group.items.map((item) => {
                                const isActive = pathname === item.url
                                return (
                                    <SidebarMenuItem key={item.title}>
                                        <SidebarMenuButton asChild isActive={isActive} tooltip={item.title}>
                                            <Link href={item.url}>
                                                {item.icon && <item.icon />}
                                                <span>{item.title}</span>
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                )
                            })}
                        </SidebarMenu>
                    </SidebarGroup>
                ))}
            </SidebarContent>
            <SidebarFooter>
                <div className="p-4 text-xs text-muted-foreground font-mono">
                    <div>STATUS: ONLINE</div>
                    <div>v2.1.0-RC</div>
                </div>
            </SidebarFooter>
            <SidebarRail />
        </Sidebar>
    )
}
