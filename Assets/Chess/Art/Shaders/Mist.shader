// Ground mist for the ruin stage: a big horizontal quad, drifting noise (two scrolling layers of one small
// tiling texture), kept clear over the board (_Hole) and fading out at the edges. Alpha-blended, no depth write.
Shader "Chess/Mist"
{
    Properties
    {
        _Color ("Color", Color) = (0.55, 0.63, 0.78, 0.6)
        _MainTex ("Noise", 2D) = "white" {}
        _Tiling ("Tiling", Float) = 3
        _Drift ("Drift", Vector) = (0.012, 0.006, -0.008, 0.01)
        _Hole ("Clear Radius (uv)", Float) = 0.17
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" }
        ZWrite Off Cull Off
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            fixed4 _Color;
            float _Tiling, _Hole;
            float4 _Drift;

            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; UNITY_FOG_COORDS(1) };

            v2f vert(appdata_base v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.texcoord.xy;
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                float2 uv = i.uv * _Tiling;
                float n = tex2D(_MainTex, uv + _Time.y * _Drift.xy).a * tex2D(_MainTex, uv * 1.7 + _Time.y * _Drift.zw).a * 2;
                float r = distance(i.uv, 0.5);
                float mask = smoothstep(_Hole, _Hole + 0.08, r) * smoothstep(0.5, 0.36, r);
                fixed4 c = fixed4(_Color.rgb, saturate(n * mask * _Color.a));
                UNITY_APPLY_FOG(i.fogCoord, c);
                return c;
            }
            ENDCG
        }
    }
}
